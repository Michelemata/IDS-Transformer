<<<<<<< HEAD
import torch
import numpy as np
from torch.utils.data import DataLoader
from scipy.spatial.distance import cdist
from dataset import TemporalWindowDataset


def calculate_unsupervised_threshold(model, df_val, cat_cols, cont_cols, config):
    """
    Evaluates the benign Validation Set to compute the spatial centroid
    and establish the anomaly threshold based on the hybrid score.

    The hybrid score combines two indicators of anomaly:
    1. Reconstruction Error (MSE): How poorly the model reconstructs the masked features.
    2. Spatial Distance: How far the packet's latent representation is from the normal centroid.
    """
    print(f"\n[*] Calculating Benign Centroid and Hybrid Threshold ({config.threshold_percentile}th Percentile)...")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.eval()

    val_ds = TemporalWindowDataset(df_val, cat_cols, cont_cols, config.max_seq_len)
    val_dl = DataLoader(val_ds, batch_size=config.batch_size, shuffle=False)

    mse_list, z_list = [], []

    # Disable gradient tracking to save VRAM and compute faster during inference
    with torch.no_grad():
        for b_cat, b_cont, b_mask, _ in val_dl:
            b_cat, b_cont, b_mask = b_cat.to(device), b_cont.to(device), b_mask.to(device)

            # Extract Mean Squared Error and the latent vector (Z)
            mse, z = model.compute_anomaly_features(b_cat, b_cont, b_mask)
            mse_list.extend(mse.cpu().numpy())
            z_list.append(z.cpu().numpy())

    mse_array = np.array(mse_list)
    z_array = np.vstack(z_list)

    # Compute Spatial Centroid (mean of benign latent representations)
    centroid = z_array.mean(axis=0)

    # Compute Cosine Distances from the centroid
    distances = cdist(z_array, centroid.reshape(1, -1), metric='cosine').flatten()

    # Statistical safety net: replace any NaN values with 0.0 to avoid breaking the normalization
    distances = np.nan_to_num(distances, nan=0.0)
    mse_array = np.nan_to_num(mse_array, nan=0.0)

    # Z-score normalization parameters
    mse_norm_params = (mse_array.mean(), mse_array.std() + 1e-8)
    dist_norm_params = (distances.mean(), distances.std() + 1e-8)

    # Normalize metrics to safely combine them
    mse_norm = (mse_array - mse_norm_params[0]) / mse_norm_params[1]
    dist_norm = (distances - dist_norm_params[0]) / dist_norm_params[1]

    # Hybrid Score combines reconstruction error (MSE) and spatial alienation (Distance)
    hybrid_scores = mse_norm + dist_norm

    # Compute the upper bound threshold based on the specified percentile
    threshold = np.percentile(hybrid_scores, config.threshold_percentile)

    print(f"    -> Hybrid Physiological Threshold: > {threshold:.4f}")

    return threshold, hybrid_scores, centroid, mse_norm_params, dist_norm_params
=======
import torch
import numpy as np
from torch.utils.data import DataLoader
from scipy.spatial.distance import cdist
from dataset import TemporalWindowDataset


def calculate_unsupervised_threshold(model, df_val, cat_cols, cont_cols, config):
    """
    Evaluates the benign Validation Set to compute the spatial centroid
    and establish the anomaly threshold based on the hybrid score.

    The hybrid score combines two indicators of anomaly:
    1. Reconstruction Error (MSE): How poorly the model reconstructs the masked features.
    2. Spatial Distance: How far the packet's latent representation is from the normal centroid.
    """
    print(f"\n[*] Calculating Benign Centroid and Hybrid Threshold ({config.threshold_percentile}th Percentile)...")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.eval()

    val_ds = TemporalWindowDataset(df_val, cat_cols, cont_cols, config.max_seq_len)
    val_dl = DataLoader(val_ds, batch_size=config.batch_size, shuffle=False)

    mse_list, z_list = [], []

    # Disable gradient tracking to save VRAM and compute faster during inference
    with torch.no_grad():
        for b_cat, b_cont, b_mask, _ in val_dl:
            b_cat, b_cont, b_mask = b_cat.to(device), b_cont.to(device), b_mask.to(device)

            # Extract Mean Squared Error and the latent vector (Z)
            mse, z = model.compute_anomaly_features(b_cat, b_cont, b_mask)
            mse_list.extend(mse.cpu().numpy())
            z_list.append(z.cpu().numpy())

    mse_array = np.array(mse_list)
    z_array = np.vstack(z_list)

    # Compute Spatial Centroid (mean of benign latent representations)
    centroid = z_array.mean(axis=0)

    # Compute Cosine Distances from the centroid
    distances = cdist(z_array, centroid.reshape(1, -1), metric='cosine').flatten()

    # Statistical safety net: replace any NaN values with 0.0 to avoid breaking the normalization
    distances = np.nan_to_num(distances, nan=0.0)
    mse_array = np.nan_to_num(mse_array, nan=0.0)

    # Z-score normalization parameters
    mse_norm_params = (mse_array.mean(), mse_array.std() + 1e-8)
    dist_norm_params = (distances.mean(), distances.std() + 1e-8)

    # Normalize metrics to safely combine them
    mse_norm = (mse_array - mse_norm_params[0]) / mse_norm_params[1]
    dist_norm = (distances - dist_norm_params[0]) / dist_norm_params[1]

    # Hybrid Score combines reconstruction error (MSE) and spatial alienation (Distance)
    hybrid_scores = mse_norm + dist_norm

    # Compute the upper bound threshold based on the specified percentile
    threshold = np.percentile(hybrid_scores, config.threshold_percentile)

    print(f"    -> Hybrid Physiological Threshold: > {threshold:.4f}")

    return threshold, hybrid_scores, centroid, mse_norm_params, dist_norm_params
>>>>>>> ffcacd5028658b79102cd438e59c1bb21b886285
