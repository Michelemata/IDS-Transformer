<<<<<<< HEAD
import time
import torch
import numpy as np
from torch.utils.data import DataLoader
from scipy.spatial.distance import cdist
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix
from dataset import TemporalWindowDataset

def run_evaluation(model, df_test, cat_cols, cont_cols, threshold, centroid, mse_params, dist_params, config):
    """
    Executes the inference phase on the test set, applies the hybrid threshold,
    and computes final performance metrics for anomaly detection.
    """
    print(f"\n[*] Inference Phase (Threshold: > {threshold:.4f})")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Set model to evaluation mode to disable Dropout and Batch Normalization updates
    model.eval()

    test_ds = TemporalWindowDataset(df_test, cat_cols, cont_cols, config.max_seq_len)
    test_dl = DataLoader(test_ds, batch_size=config.batch_size, shuffle=False)

    mse_list, z_list, labels = [], [], []
    total_time = 0.0

    # Disable gradient calculation to heavily optimize VRAM and maximize inference speed
    with torch.no_grad():
        for b_cat, b_cont, b_mask, b_labels in test_dl:
            b_cat, b_cont, b_mask = b_cat.to(device), b_cont.to(device), b_mask.to(device)

            # Start latency timer for the current batch
            start = time.perf_counter()

            # Extract reconstruction error and latent vector
            batch_mse, z = model.compute_anomaly_features(b_cat, b_cont, b_mask)

            # Stop timer and accumulate total inference time
            total_time += (time.perf_counter() - start)

            mse_list.extend(batch_mse.cpu().numpy())
            z_list.append(z.cpu().numpy())
            labels.extend(b_labels.numpy())

    mse_array = np.array(mse_list)
    z_array = np.vstack(z_list)
    labels = np.array(labels)

    # Safety filter to remove invalid predictions (NaNs)
    valid_mask = ~np.isnan(mse_array)
    mse_array = mse_array[valid_mask]
    z_array = z_array[valid_mask]
    labels = labels[valid_mask]

    # Compute Cosine Distances relative to the benign centroid
    distances = cdist(z_array, centroid.reshape(1, -1), metric='cosine').flatten()

    # Z-score normalization using validation parameters in order to prevent data leakage
    mse_norm = (mse_array - mse_params[0]) / mse_params[1]
    dist_norm = (distances - dist_params[0]) / dist_params[1]

    # Combine normalized metrics into the Hybrid Score
    hybrid_scores = mse_norm + dist_norm

    # Handle edge cases where the test set might lack one of the classes (e.g., all benign traffic)
    unique_classes = np.unique(labels)
    if len(unique_classes) == 1:
        print(f"    [!] Test Set contains only class {unique_classes[0]}. AUC cannot be computed.")
        auc_score = 0.0
    else:
        auc_score = roc_auc_score(labels, hybrid_scores)

    # Single-tail unsupervised classification (Out-of-Bound detection)
    preds = (hybrid_scores > threshold).astype(int)

    # Compute classification metrics
    f1 = f1_score(labels, preds, zero_division=0)
    precision = precision_score(labels, preds, zero_division=0)
    recall = recall_score(labels, preds, zero_division=0)
    accuracy = accuracy_score(labels, preds)

    # Extract absolute values from the confusion matrix
    tn, fp, fn, tp = confusion_matrix(labels, preds).ravel()

    # Calculate average latency per temporal window in milliseconds
    latency_ms = (total_time / len(test_ds)) * 1000
    print(f"[+] AUC: {auc_score:.4f} | F1: {f1:.4f} (Prec: {precision:.4f}, Rec: {recall:.4f}) | Latenza: {latency_ms:.2f} ms")

    return hybrid_scores, labels, auc_score, f1, precision, recall, accuracy, tn, fp, fn, tp, latency_ms
=======
import time
import torch
import numpy as np
from torch.utils.data import DataLoader
from scipy.spatial.distance import cdist
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix
from dataset import TemporalWindowDataset

def run_evaluation(model, df_test, cat_cols, cont_cols, threshold, centroid, mse_params, dist_params, config):
    """
    Executes the inference phase on the test set, applies the hybrid threshold,
    and computes final performance metrics for anomaly detection.
    """
    print(f"\n[*] Inference Phase (Threshold: > {threshold:.4f})")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Set model to evaluation mode to disable Dropout and Batch Normalization updates
    model.eval()

    test_ds = TemporalWindowDataset(df_test, cat_cols, cont_cols, config.max_seq_len)
    test_dl = DataLoader(test_ds, batch_size=config.batch_size, shuffle=False)

    mse_list, z_list, labels = [], [], []
    total_time = 0.0

    # Disable gradient calculation to heavily optimize VRAM and maximize inference speed
    with torch.no_grad():
        for b_cat, b_cont, b_mask, b_labels in test_dl:
            b_cat, b_cont, b_mask = b_cat.to(device), b_cont.to(device), b_mask.to(device)

            # Start latency timer for the current batch
            start = time.perf_counter()

            # Extract reconstruction error and latent vector
            batch_mse, z = model.compute_anomaly_features(b_cat, b_cont, b_mask)

            # Stop timer and accumulate total inference time
            total_time += (time.perf_counter() - start)

            mse_list.extend(batch_mse.cpu().numpy())
            z_list.append(z.cpu().numpy())
            labels.extend(b_labels.numpy())

    mse_array = np.array(mse_list)
    z_array = np.vstack(z_list)
    labels = np.array(labels)

    # Safety filter to remove invalid predictions (NaNs)
    valid_mask = ~np.isnan(mse_array)
    mse_array = mse_array[valid_mask]
    z_array = z_array[valid_mask]
    labels = labels[valid_mask]

    # Compute Cosine Distances relative to the benign centroid
    distances = cdist(z_array, centroid.reshape(1, -1), metric='cosine').flatten()

    # Z-score normalization using validation parameters in order to prevent data leakage
    mse_norm = (mse_array - mse_params[0]) / mse_params[1]
    dist_norm = (distances - dist_params[0]) / dist_params[1]

    # Combine normalized metrics into the Hybrid Score
    hybrid_scores = mse_norm + dist_norm

    # Handle edge cases where the test set might lack one of the classes (e.g., all benign traffic)
    unique_classes = np.unique(labels)
    if len(unique_classes) == 1:
        print(f"    [!] Test Set contains only class {unique_classes[0]}. AUC cannot be computed.")
        auc_score = 0.0
    else:
        auc_score = roc_auc_score(labels, hybrid_scores)

    # Single-tail unsupervised classification (Out-of-Bound detection)
    preds = (hybrid_scores > threshold).astype(int)

    # Compute classification metrics
    f1 = f1_score(labels, preds, zero_division=0)
    precision = precision_score(labels, preds, zero_division=0)
    recall = recall_score(labels, preds, zero_division=0)
    accuracy = accuracy_score(labels, preds)

    # Extract absolute values from the confusion matrix
    tn, fp, fn, tp = confusion_matrix(labels, preds).ravel()

    # Calculate average latency per temporal window in milliseconds
    latency_ms = (total_time / len(test_ds)) * 1000
    print(f"[+] AUC: {auc_score:.4f} | F1: {f1:.4f} (Prec: {precision:.4f}, Rec: {recall:.4f}) | Latenza: {latency_ms:.2f} ms")

    return hybrid_scores, labels, auc_score, f1, precision, recall, accuracy, tn, fp, fn, tp, latency_ms
>>>>>>> ffcacd5028658b79102cd438e59c1bb21b886285
