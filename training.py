<<<<<<< HEAD
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import DataLoader
from tqdm import tqdm
from dataset import TemporalWindowDataset
from model import TabularTokenizer, SAINTLayer
from utils import EarlyStopping


class InfoNCELoss(nn.Module):
    """
    Computes InfoNCE (Information Noise-Contrastive Estimation) loss
    for contrastive learning. It pulls together embeddings of augmented views
    from the same sample (positives) while pushing apart all other samples in the batch (negatives).
    """
    def __init__(self, temperature):
        super().__init__()
        self.temp = temperature
        self.crit = nn.CrossEntropyLoss()

    def forward(self, z_i, z_j):
        # L2 Normalize the latent vectors to project them onto a unit hypersphere
        z_i, z_j = F.normalize(z_i, dim=1), F.normalize(z_j, dim=1)

        # Compute cosine similarity logits scaled by the temperature parameter
        logits = torch.matmul(z_i, z_j.T) / self.temp
        labels = torch.arange(logits.size(0), device=logits.device)

        # Symmetric cross-entropy to handle both z_i -> z_j and z_j -> z_i directions
        return (self.crit(logits, labels) + self.crit(logits.T, labels)) / 2


class Self_Supervised_Learning(nn.Module):
    """
    Wrapper for SAINT self-supervised training using
    Feature Masking (reconstruction) and Contrastive Learning (MixUp).
    """
    def __init__(self, tokenizer, saint_blocks, cat_dims, num_cont, embed_dim=32, mask_prob=0.3,
                 contrastive_weight=0.5, temperature=0.7):
        super().__init__()
        self.tokenizer = tokenizer

        # Use ModuleList to iterate and pass the padding mask to each block
        self.saint_blocks = nn.ModuleList(saint_blocks)
        self.mask_prob = mask_prob
        self.num_cat, self.num_cont = len(cat_dims), num_cont
        self.cw = contrastive_weight

        # Learnable embedding used to replace explicitly masked tokens
        self.mask_token = nn.Parameter(torch.randn(1, 1, 1, embed_dim))

        # Reconstructors map the latent embeddings back to their original feature space
        self.cat_reconstructors = nn.ModuleList([nn.Linear(embed_dim, dim) for dim in cat_dims])
        self.cont_reconstructor = nn.Sequential(
            nn.Linear(embed_dim, embed_dim // 2),
            nn.ReLU(),
            nn.Linear(embed_dim // 2, 1)
        )

        self.contrastive_loss_fn = InfoNCELoss(temperature=temperature)

        # Projection head maps the mean-pooled sequence into a lower-dimensional space for contrastive loss
        self.proj_head = nn.Sequential(
            nn.Linear(embed_dim, embed_dim),
            nn.ReLU(),
            nn.Linear(embed_dim, 128)
        )

    def _tabular_mixup(self, x_cat, x_cont, prob=0.2):
        """Applies MixUp data augmentation for the contrastive learning branch."""
        B, W, F_cat = x_cat.shape
        _, _, F_cont = x_cont.shape
        perm = torch.randperm(B, device=x_cat.device)
        m_cat = torch.rand((B, W, F_cat), device=x_cat.device) < prob
        m_cont = torch.rand((B, W, F_cont), device=x_cont.device) < prob
        return torch.where(m_cat, x_cat[perm], x_cat), torch.where(m_cont, x_cont[perm], x_cont)

    def forward(self, x_cat, x_cont, padding_mask):
        B, W = x_cat.shape[0], x_cat.shape[1]

        # Branch 1: Feature Masking and Reconstruction
        emb_v1 = self.tokenizer(x_cat, x_cont)
        Tot_F = emb_v1.shape[2]

        # Generate a boolean mask based on the mask_prob threshold
        ssl_mask = torch.bernoulli(torch.full((B, W, Tot_F), self.mask_prob, device=emb_v1.device)).bool()

        # Replace selected tokens with the universal learned mask_token
        masked_v1 = emb_v1.clone()
        masked_v1[ssl_mask] = self.mask_token

        enc_v1 = masked_v1
        for block in self.saint_blocks:
            enc_v1 = block(enc_v1, padding_mask)

        # Compute reconstruction loss excluding padded tokens
        loss_recon = self._compute_recon_loss(enc_v1, x_cat, x_cont, ssl_mask, padding_mask)

        # Branch 2: Tabular MixUp for Contrastive Learning
        x_cat_m, x_cont_m = self._tabular_mixup(x_cat, x_cont)
        emb_v2 = self.tokenizer(x_cat_m, x_cont_m)

        enc_v2 = emb_v2
        for block in self.saint_blocks:
            enc_v2 = block(enc_v2, padding_mask)

        # Mean pooling over sequence; padded tokens are ignored as they were zeroed out
        z1 = self.proj_head(enc_v1.mean(dim=(1, 2)))
        z2 = self.proj_head(enc_v2.mean(dim=(1, 2)))

        loss_cont = self.contrastive_loss_fn(z1, z2)

        # Final loss is a weighted sum of reconstruction and contrastive objectives
        return loss_recon + (self.cw * loss_cont)

    def compute_anomaly_features(self, x_cat, x_cont, padding_mask):
        """Extracts reconstruction errors (MSE) and latent representations during inference."""
        B, W = x_cat.shape[0], x_cat.shape[1]
        emb = self.tokenizer(x_cat, x_cont)
        Tot_F = emb.shape[2]

        # Masking branch to compute reconstruction error
        ssl_mask = torch.bernoulli(torch.full((B, W, Tot_F), self.mask_prob, device=emb.device)).bool()
        masked = emb.clone()
        masked[ssl_mask] = self.mask_token

        enc = masked
        for block in self.saint_blocks:
            enc = block(enc, padding_mask)

        batch_mse = torch.zeros(B, device=x_cat.device)
        for b in range(B):
            batch_mse[b] = self._compute_recon_loss(enc[b:b+1], x_cat[b:b+1], x_cont[b:b+1], ssl_mask[b:b+1], padding_mask[b:b+1])

        # Extract latent vector for spatial distance anomaly detection
        z = self.proj_head(enc.mean(dim=(1, 2)))

        return batch_mse, z

    def _compute_recon_loss(self, enc, x_cat, x_cont, ssl_mask, padding_mask):
        """Calculates loss exclusively on valid (non-padded) masked tokens."""
        total_loss = 0.0
        cat_enc, cont_enc = enc[:, :, :self.num_cat, :], enc[:, :, self.num_cat:, :]
        m_cat, m_cont = ssl_mask[:, :, :self.num_cat], ssl_mask[:, :, self.num_cat:]

        # Create a valid mask: only compute loss if the token was masked AND it is not a padding token
        valid_mask_cat = m_cat & (~padding_mask.unsqueeze(-1))
        valid_mask_cont = m_cont & (~padding_mask.unsqueeze(-1))

        # CrossEntropy for categorical features
        for i in range(self.num_cat):
            preds = self.cat_reconstructors[i](cat_enc[:, :, i, :])
            if valid_mask_cat[:, :, i].sum() > 0:
                total_loss += F.cross_entropy(preds[valid_mask_cat[:, :, i]], x_cat[:, :, i][valid_mask_cat[:, :, i]])

        # Mean Squared Error for continuous features
        preds_cont = self.cont_reconstructor(cont_enc).squeeze(-1)
        if valid_mask_cont.sum() > 0:
            total_loss += F.mse_loss(preds_cont[valid_mask_cont], x_cont[valid_mask_cont])

        return total_loss


def train_ssl(df_train, df_val, cat_cols, cont_cols, ordinal_enc, config):
    """Executes the self-supervised training loop exclusively on benign traffic."""
    print("\n[*] Self-Supervised Training (Benign Traffic Only)")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    train_dl = DataLoader(TemporalWindowDataset(df_train, cat_cols, cont_cols, config.max_seq_len),
                          batch_size=config.batch_size, shuffle=True, drop_last=True)
    val_dl = DataLoader(TemporalWindowDataset(df_val, cat_cols, cont_cols, config.max_seq_len),
                        batch_size=config.batch_size, shuffle=False)

    cat_dims = []
    for i in range(len(cat_cols)):
        # Get the number of categories learned from the training set.
        # Add +1 since index 0 is reserved for the <UNK> (unknown) token to prevent data leakage.
        vocab_size = len(ordinal_enc.categories_[i]) + 1
        cat_dims.append(vocab_size)

    tokenizer = TabularTokenizer(cat_dims, len(cont_cols), embed_dim=config.embed_dim)
    saint_blocks = [SAINTLayer(32, 4) for _ in range(config.num_encoders)]

    model = Self_Supervised_Learning(
        tokenizer, saint_blocks, cat_dims, len(cont_cols),
        embed_dim=config.embed_dim,
        mask_prob=config.mask_prob,
        contrastive_weight=config.contrastive_weight,
        temperature=config.temperature  # Se lo passi al costruttore
    ).to(device)

    optimizer = optim.AdamW(model.parameters(), lr=config.lr, weight_decay=config.weight_decay)
    early_stop = EarlyStopping(patience=config.early_stop_patience, path='best_saint.pth')

    # Mixed precision scaler to optimize VRAM usage
    scaler = torch.amp.GradScaler()

    for epoch in range(config.epochs):
        model.train()
        train_loss = 0

        for b_cat, b_cont, b_mask, _ in tqdm(train_dl, desc=f"Epoca {epoch + 1}/{config.epochs}"):
            b_cat, b_cont, b_mask = b_cat.to(device), b_cont.to(device), b_mask.to(device)

            # Physically deallocate gradient memory for efficiency
            optimizer.zero_grad(set_to_none=True)

            # Cast forward pass to 16-bit
            with torch.amp.autocast('cuda'):
                loss = model(b_cat, b_cont, b_mask)

            # Scaled backward pass and optimizer step
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            train_loss += loss.item()

        model.eval()
        val_loss = 0
        with torch.no_grad():
            for b_cat, b_cont, b_mask, _ in val_dl:
                b_cat, b_cont, b_mask = b_cat.to(device), b_cont.to(device), b_mask.to(device)
                val_loss += model(b_cat, b_cont, b_mask).item()

        avg_train = train_loss / len(train_dl)
        avg_val = val_loss / len(val_dl)
        print(f"    -> Train Loss: {avg_train:.4f} | Val Loss: {avg_val:.4f}")

        early_stop(avg_val, model)
        if early_stop.early_stop:
            print("[!] Early Stopping triggered.")
            break

        # Clear CUDA cache to prevent memory fragmentation
        torch.cuda.empty_cache()

    # Restore the model weights from the best performing epoch on validation data
    model.load_state_dict(torch.load('best_saint.pth', weights_only=True))
    return model
=======
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import DataLoader
from tqdm import tqdm
from dataset import TemporalWindowDataset
from model import TabularTokenizer, SAINTLayer
from utils import EarlyStopping


class InfoNCELoss(nn.Module):
    """
    Computes InfoNCE (Information Noise-Contrastive Estimation) loss
    for contrastive learning. It pulls together embeddings of augmented views
    from the same sample (positives) while pushing apart all other samples in the batch (negatives).
    """
    def __init__(self, temperature):
        super().__init__()
        self.temp = temperature
        self.crit = nn.CrossEntropyLoss()

    def forward(self, z_i, z_j):
        # L2 Normalize the latent vectors to project them onto a unit hypersphere
        z_i, z_j = F.normalize(z_i, dim=1), F.normalize(z_j, dim=1)

        # Compute cosine similarity logits scaled by the temperature parameter
        logits = torch.matmul(z_i, z_j.T) / self.temp
        labels = torch.arange(logits.size(0), device=logits.device)

        # Symmetric cross-entropy to handle both z_i -> z_j and z_j -> z_i directions
        return (self.crit(logits, labels) + self.crit(logits.T, labels)) / 2


class Self_Supervised_Learning(nn.Module):
    """
    Wrapper for SAINT self-supervised training using
    Feature Masking (reconstruction) and Contrastive Learning (MixUp).
    """
    def __init__(self, tokenizer, saint_blocks, cat_dims, num_cont, embed_dim=32, mask_prob=0.3,
                 contrastive_weight=0.5, temperature=0.7):
        super().__init__()
        self.tokenizer = tokenizer

        # Use ModuleList to iterate and pass the padding mask to each block
        self.saint_blocks = nn.ModuleList(saint_blocks)
        self.mask_prob = mask_prob
        self.num_cat, self.num_cont = len(cat_dims), num_cont
        self.cw = contrastive_weight

        # Learnable embedding used to replace explicitly masked tokens
        self.mask_token = nn.Parameter(torch.randn(1, 1, 1, embed_dim))

        # Reconstructors map the latent embeddings back to their original feature space
        self.cat_reconstructors = nn.ModuleList([nn.Linear(embed_dim, dim) for dim in cat_dims])
        self.cont_reconstructor = nn.Sequential(
            nn.Linear(embed_dim, embed_dim // 2),
            nn.ReLU(),
            nn.Linear(embed_dim // 2, 1)
        )

        self.contrastive_loss_fn = InfoNCELoss(temperature=temperature)

        # Projection head maps the mean-pooled sequence into a lower-dimensional space for contrastive loss
        self.proj_head = nn.Sequential(
            nn.Linear(embed_dim, embed_dim),
            nn.ReLU(),
            nn.Linear(embed_dim, 128)
        )

    def _tabular_mixup(self, x_cat, x_cont, prob=0.2):
        """Applies MixUp data augmentation for the contrastive learning branch."""
        B, W, F_cat = x_cat.shape
        _, _, F_cont = x_cont.shape
        perm = torch.randperm(B, device=x_cat.device)
        m_cat = torch.rand((B, W, F_cat), device=x_cat.device) < prob
        m_cont = torch.rand((B, W, F_cont), device=x_cont.device) < prob
        return torch.where(m_cat, x_cat[perm], x_cat), torch.where(m_cont, x_cont[perm], x_cont)

    def forward(self, x_cat, x_cont, padding_mask):
        B, W = x_cat.shape[0], x_cat.shape[1]

        # Branch 1: Feature Masking and Reconstruction
        emb_v1 = self.tokenizer(x_cat, x_cont)
        Tot_F = emb_v1.shape[2]

        # Generate a boolean mask based on the mask_prob threshold
        ssl_mask = torch.bernoulli(torch.full((B, W, Tot_F), self.mask_prob, device=emb_v1.device)).bool()

        # Replace selected tokens with the universal learned mask_token
        masked_v1 = emb_v1.clone()
        masked_v1[ssl_mask] = self.mask_token

        enc_v1 = masked_v1
        for block in self.saint_blocks:
            enc_v1 = block(enc_v1, padding_mask)

        # Compute reconstruction loss excluding padded tokens
        loss_recon = self._compute_recon_loss(enc_v1, x_cat, x_cont, ssl_mask, padding_mask)

        # Branch 2: Tabular MixUp for Contrastive Learning
        x_cat_m, x_cont_m = self._tabular_mixup(x_cat, x_cont)
        emb_v2 = self.tokenizer(x_cat_m, x_cont_m)

        enc_v2 = emb_v2
        for block in self.saint_blocks:
            enc_v2 = block(enc_v2, padding_mask)

        # Mean pooling over sequence; padded tokens are ignored as they were zeroed out
        z1 = self.proj_head(enc_v1.mean(dim=(1, 2)))
        z2 = self.proj_head(enc_v2.mean(dim=(1, 2)))

        loss_cont = self.contrastive_loss_fn(z1, z2)

        # Final loss is a weighted sum of reconstruction and contrastive objectives
        return loss_recon + (self.cw * loss_cont)

    def compute_anomaly_features(self, x_cat, x_cont, padding_mask):
        """Extracts reconstruction errors (MSE) and latent representations during inference."""
        B, W = x_cat.shape[0], x_cat.shape[1]
        emb = self.tokenizer(x_cat, x_cont)
        Tot_F = emb.shape[2]

        # Masking branch to compute reconstruction error
        ssl_mask = torch.bernoulli(torch.full((B, W, Tot_F), self.mask_prob, device=emb.device)).bool()
        masked = emb.clone()
        masked[ssl_mask] = self.mask_token

        enc = masked
        for block in self.saint_blocks:
            enc = block(enc, padding_mask)

        batch_mse = torch.zeros(B, device=x_cat.device)
        for b in range(B):
            batch_mse[b] = self._compute_recon_loss(enc[b:b+1], x_cat[b:b+1], x_cont[b:b+1], ssl_mask[b:b+1], padding_mask[b:b+1])

        # Extract latent vector for spatial distance anomaly detection
        z = self.proj_head(enc.mean(dim=(1, 2)))

        return batch_mse, z

    def _compute_recon_loss(self, enc, x_cat, x_cont, ssl_mask, padding_mask):
        """Calculates loss exclusively on valid (non-padded) masked tokens."""
        total_loss = 0.0
        cat_enc, cont_enc = enc[:, :, :self.num_cat, :], enc[:, :, self.num_cat:, :]
        m_cat, m_cont = ssl_mask[:, :, :self.num_cat], ssl_mask[:, :, self.num_cat:]

        # Create a valid mask: only compute loss if the token was masked AND it is not a padding token
        valid_mask_cat = m_cat & (~padding_mask.unsqueeze(-1))
        valid_mask_cont = m_cont & (~padding_mask.unsqueeze(-1))

        # CrossEntropy for categorical features
        for i in range(self.num_cat):
            preds = self.cat_reconstructors[i](cat_enc[:, :, i, :])
            if valid_mask_cat[:, :, i].sum() > 0:
                total_loss += F.cross_entropy(preds[valid_mask_cat[:, :, i]], x_cat[:, :, i][valid_mask_cat[:, :, i]])

        # Mean Squared Error for continuous features
        preds_cont = self.cont_reconstructor(cont_enc).squeeze(-1)
        if valid_mask_cont.sum() > 0:
            total_loss += F.mse_loss(preds_cont[valid_mask_cont], x_cont[valid_mask_cont])

        return total_loss


def train_ssl(df_train, df_val, cat_cols, cont_cols, ordinal_enc, config):
    """Executes the self-supervised training loop exclusively on benign traffic."""
    print("\n[*] Self-Supervised Training (Benign Traffic Only)")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    train_dl = DataLoader(TemporalWindowDataset(df_train, cat_cols, cont_cols, config.max_seq_len),
                          batch_size=config.batch_size, shuffle=True, drop_last=True)
    val_dl = DataLoader(TemporalWindowDataset(df_val, cat_cols, cont_cols, config.max_seq_len),
                        batch_size=config.batch_size, shuffle=False)

    cat_dims = []
    for i in range(len(cat_cols)):
        # Get the number of categories learned from the training set.
        # Add +1 since index 0 is reserved for the <UNK> (unknown) token to prevent data leakage.
        vocab_size = len(ordinal_enc.categories_[i]) + 1
        cat_dims.append(vocab_size)

    tokenizer = TabularTokenizer(cat_dims, len(cont_cols), embed_dim=config.embed_dim)
    saint_blocks = [SAINTLayer(32, 4) for _ in range(config.num_encoders)]

    model = Self_Supervised_Learning(
        tokenizer, saint_blocks, cat_dims, len(cont_cols),
        embed_dim=config.embed_dim,
        mask_prob=config.mask_prob,
        contrastive_weight=config.contrastive_weight,
        temperature=config.temperature  # Se lo passi al costruttore
    ).to(device)

    optimizer = optim.AdamW(model.parameters(), lr=config.lr, weight_decay=config.weight_decay)
    early_stop = EarlyStopping(patience=config.early_stop_patience, path='best_saint.pth')

    # Mixed precision scaler to optimize VRAM usage
    scaler = torch.amp.GradScaler()

    for epoch in range(config.epochs):
        model.train()
        train_loss = 0

        for b_cat, b_cont, b_mask, _ in tqdm(train_dl, desc=f"Epoca {epoch + 1}/{config.epochs}"):
            b_cat, b_cont, b_mask = b_cat.to(device), b_cont.to(device), b_mask.to(device)

            # Physically deallocate gradient memory for efficiency
            optimizer.zero_grad(set_to_none=True)

            # Cast forward pass to 16-bit
            with torch.amp.autocast('cuda'):
                loss = model(b_cat, b_cont, b_mask)

            # Scaled backward pass and optimizer step
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            train_loss += loss.item()

        model.eval()
        val_loss = 0
        with torch.no_grad():
            for b_cat, b_cont, b_mask, _ in val_dl:
                b_cat, b_cont, b_mask = b_cat.to(device), b_cont.to(device), b_mask.to(device)
                val_loss += model(b_cat, b_cont, b_mask).item()

        avg_train = train_loss / len(train_dl)
        avg_val = val_loss / len(val_dl)
        print(f"    -> Train Loss: {avg_train:.4f} | Val Loss: {avg_val:.4f}")

        early_stop(avg_val, model)
        if early_stop.early_stop:
            print("[!] Early Stopping triggered.")
            break

        # Clear CUDA cache to prevent memory fragmentation
        torch.cuda.empty_cache()

    # Restore the model weights from the best performing epoch on validation data
    model.load_state_dict(torch.load('best_saint.pth', weights_only=True))
    return model
>>>>>>> ffcacd5028658b79102cd438e59c1bb21b886285
