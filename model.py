<<<<<<< HEAD
import torch
import torch.nn as nn


class TabularTokenizer(nn.Module):
    """
    Maps both categorical and continuous tabular features into a unified
    embedding space of size `embed_dim`.
    """
    def __init__(self, cat_dims, num_cont, embed_dim=32):
        super().__init__()

        # Categorical features use standard look-up embeddings
        self.cat_embeds = nn.ModuleList([nn.Embedding(d, embed_dim) for d in cat_dims])

        # Continuous features are projected via a linear layer
        self.cont_embeds = nn.ModuleList([nn.Linear(1, embed_dim) for _ in range(num_cont)])

    def forward(self, x_cat, x_cont):
        cat_out = [emb(x_cat[..., i]) for i, emb in enumerate(self.cat_embeds)]
        cont_out = [emb(x_cont[..., i].unsqueeze(-1)) for i, emb in enumerate(self.cont_embeds)]

        # Stack along a new feature dimension to create a 3D tensor (Batch, Features, Embed_Dim)
        return torch.stack(cat_out + cont_out, dim=2)


class FeedForward(nn.Module):
    """
    Standard Multi-Layer Perceptron (MLP) block used within Transformer layers
    to provide non-linear feature transformation after attention operations.
    """
    def __init__(self, dim, hidden_dim, dropout=0.1):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, dim),
            nn.Dropout(dropout)
        )

    def forward(self, x): return self.net(x)


class IntraSampleAttention(nn.Module):
    """
    Computes self-attention ACROSS FEATURES of the same network flow (row).
    Helps the model understand the relationship between different packet metrics.
    """
    def __init__(self, embed_dim, num_heads, dropout):
        super().__init__()
        self.attn = nn.MultiheadAttention(embed_dim, num_heads, dropout=dropout, batch_first=True)
        self.ln1 = nn.LayerNorm(embed_dim)
        self.ff = FeedForward(embed_dim, embed_dim * 4, dropout)
        self.ln2 = nn.LayerNorm(embed_dim)

    def forward(self, x):
        B, W, F, D = x.shape

        # Reshape to merge Batch and Window dimensions for feature-wise attention
        x_res = x.view(B * W, F, D)
        attn_out, _ = self.attn(x_res, x_res, x_res)

        x_res = self.ln1(x_res + attn_out)
        x_res = self.ln2(x_res + self.ff(x_res))

        # Restore original 4D shape
        return x_res.view(B, W, F, D)


class InterSampleAttention(nn.Module):
    """
    Computes self-attention ACROSS SAMPLES (rows) within the same temporal window.
    Helps the model capture temporal patterns and interactions between different flows.
    """
    def __init__(self, embed_dim, num_heads, dropout):
        super().__init__()
        self.attn = nn.MultiheadAttention(embed_dim, num_heads, dropout=dropout, batch_first=True)
        self.ln1 = nn.LayerNorm(embed_dim)
        self.ff = FeedForward(embed_dim, embed_dim * 4, dropout)
        self.ln2 = nn.LayerNorm(embed_dim)

    def forward(self, x, padding_mask):
        B, W, F, D = x.shape

        # Transpose and reshape to attend across the Window (W) dimension
        x_res = x.transpose(1, 2).contiguous().view(B * F, W, D)

        # Replicate the padding mask for all features
        mask_repeated = padding_mask.repeat_interleave(F, dim=0)

        # Apply attention, masking out padded (dummy) flows
        attn_out, _ = self.attn(x_res, x_res, x_res, key_padding_mask=mask_repeated)

        x_res = self.ln1(x_res + attn_out)
        x_res = self.ln2(x_res + self.ff(x_res))

        # Restore original shape
        return x_res.view(B, F, W, D).transpose(1, 2).contiguous()


class SAINTLayer(nn.Module):
    """
    A complete SAINT block combining Intra-sample and Inter-sample attention.
    """
    def __init__(self, embed_dim, num_heads, dropout=0.1):
        super().__init__()
        self.intra = IntraSampleAttention(embed_dim, num_heads, dropout)
        self.inter = InterSampleAttention(embed_dim, num_heads, dropout)

    def forward(self, x, padding_mask):
        # Feature-wise interaction
        x = self.intra(x)

        # Flow-wise interaction over time
        x = self.inter(x, padding_mask)

        # Strictly zero-out padded elements to avoid leaking noise to downstream tasks
        expanded_mask = padding_mask.unsqueeze(-1).unsqueeze(-1)
        return x.masked_fill(expanded_mask, 0.0)
=======
import torch
import torch.nn as nn


class TabularTokenizer(nn.Module):
    """
    Maps both categorical and continuous tabular features into a unified
    embedding space of size `embed_dim`.
    """
    def __init__(self, cat_dims, num_cont, embed_dim=32):
        super().__init__()

        # Categorical features use standard look-up embeddings
        self.cat_embeds = nn.ModuleList([nn.Embedding(d, embed_dim) for d in cat_dims])

        # Continuous features are projected via a linear layer
        self.cont_embeds = nn.ModuleList([nn.Linear(1, embed_dim) for _ in range(num_cont)])

    def forward(self, x_cat, x_cont):
        cat_out = [emb(x_cat[..., i]) for i, emb in enumerate(self.cat_embeds)]
        cont_out = [emb(x_cont[..., i].unsqueeze(-1)) for i, emb in enumerate(self.cont_embeds)]

        # Stack along a new feature dimension to create a 3D tensor (Batch, Features, Embed_Dim)
        return torch.stack(cat_out + cont_out, dim=2)


class FeedForward(nn.Module):
    """
    Standard Multi-Layer Perceptron (MLP) block used within Transformer layers
    to provide non-linear feature transformation after attention operations.
    """
    def __init__(self, dim, hidden_dim, dropout=0.1):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, dim),
            nn.Dropout(dropout)
        )

    def forward(self, x): return self.net(x)


class IntraSampleAttention(nn.Module):
    """
    Computes self-attention ACROSS FEATURES of the same network flow (row).
    Helps the model understand the relationship between different packet metrics.
    """
    def __init__(self, embed_dim, num_heads, dropout):
        super().__init__()
        self.attn = nn.MultiheadAttention(embed_dim, num_heads, dropout=dropout, batch_first=True)
        self.ln1 = nn.LayerNorm(embed_dim)
        self.ff = FeedForward(embed_dim, embed_dim * 4, dropout)
        self.ln2 = nn.LayerNorm(embed_dim)

    def forward(self, x):
        B, W, F, D = x.shape

        # Reshape to merge Batch and Window dimensions for feature-wise attention
        x_res = x.view(B * W, F, D)
        attn_out, _ = self.attn(x_res, x_res, x_res)

        x_res = self.ln1(x_res + attn_out)
        x_res = self.ln2(x_res + self.ff(x_res))

        # Restore original 4D shape
        return x_res.view(B, W, F, D)


class InterSampleAttention(nn.Module):
    """
    Computes self-attention ACROSS SAMPLES (rows) within the same temporal window.
    Helps the model capture temporal patterns and interactions between different flows.
    """
    def __init__(self, embed_dim, num_heads, dropout):
        super().__init__()
        self.attn = nn.MultiheadAttention(embed_dim, num_heads, dropout=dropout, batch_first=True)
        self.ln1 = nn.LayerNorm(embed_dim)
        self.ff = FeedForward(embed_dim, embed_dim * 4, dropout)
        self.ln2 = nn.LayerNorm(embed_dim)

    def forward(self, x, padding_mask):
        B, W, F, D = x.shape

        # Transpose and reshape to attend across the Window (W) dimension
        x_res = x.transpose(1, 2).contiguous().view(B * F, W, D)

        # Replicate the padding mask for all features
        mask_repeated = padding_mask.repeat_interleave(F, dim=0)

        # Apply attention, masking out padded (dummy) flows
        attn_out, _ = self.attn(x_res, x_res, x_res, key_padding_mask=mask_repeated)

        x_res = self.ln1(x_res + attn_out)
        x_res = self.ln2(x_res + self.ff(x_res))

        # Restore original shape
        return x_res.view(B, F, W, D).transpose(1, 2).contiguous()


class SAINTLayer(nn.Module):
    """
    A complete SAINT block combining Intra-sample and Inter-sample attention.
    """
    def __init__(self, embed_dim, num_heads, dropout=0.1):
        super().__init__()
        self.intra = IntraSampleAttention(embed_dim, num_heads, dropout)
        self.inter = InterSampleAttention(embed_dim, num_heads, dropout)

    def forward(self, x, padding_mask):
        # Feature-wise interaction
        x = self.intra(x)

        # Flow-wise interaction over time
        x = self.inter(x, padding_mask)

        # Strictly zero-out padded elements to avoid leaking noise to downstream tasks
        expanded_mask = padding_mask.unsqueeze(-1).unsqueeze(-1)
        return x.masked_fill(expanded_mask, 0.0)
>>>>>>> ffcacd5028658b79102cd438e59c1bb21b886285
