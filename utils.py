<<<<<<< HEAD
import os
import random
import numpy as np
import torch
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import confusion_matrix

def set_seed(seed=42):
    """
    Sets the random seed to ensure full reproducibility.
    Disables non-deterministic GPU optimizations.
    """
    # Python and OS-level Seed
    random.seed(seed)
    os.environ['PYTHONHASHSEED'] = str(seed)

    # NumPy seed for data manipulation
    np.random.seed(seed)

    # PyTorch seeds for CPU and GPU operations
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)

    # Enforce strict CUDA determinism (disables auto-tuning optimizations)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


class EarlyStopping:
    """
    Halts training if validation loss stops improving to prevent overfitting.
    """
    def __init__(self, patience, path='best_saint.pth'):
        self.patience, self.path = patience, path
        self.counter, self.best_loss, self.early_stop = 0, None, False

    def __call__(self, val_loss, model):
        """
        Evaluates the current validation loss against the historical best.
        Saves the model state if an improvement is detected.
        """
        if self.best_loss is None or val_loss < self.best_loss:
            # Improvement detected: save weights and reset patience counter
            self.best_loss = val_loss
            torch.save(model.state_dict(), self.path)
            self.counter = 0
        else:
            # No improvement: increment counter and check stopping condition
            self.counter += 1
            if self.counter >= self.patience:
                self.early_stop = True


def plot_kde_distribution(val_scores, test_scores, test_labels, threshold, percentile, window_size):
    """
    Generates and saves a Kernel Density Estimation (KDE) plot of the anomaly scores.
    Visually demonstrates the separation between benign traffic and malicious traffic,
    while mapping the unsupervised threshold.
    """
    print(f"\n[*] Generating KDE Plot (W={window_size}s)...")
    sns.set_theme(style="whitegrid", context="paper", font_scale=1.2)
    plt.figure(figsize=(10, 5))

    # Plot the baseline physiological distribution (Validation Set)
    sns.kdeplot(val_scores, fill=True, color="#3182ce", label="Benign Traffic", alpha=0.6)

    # Filter and plot the malicious score distribution from the Test Set
    attack_scores = test_scores[test_labels == 1]
    if len(attack_scores) > 0:
        sns.kdeplot(attack_scores, fill=True, color="#e53e3e", label="Malicious Traffic", alpha=0.6)

    # Plot the single upper-bound anomaly threshold
    plt.axvline(threshold, color="#1a202c", linestyle="--", linewidth=2.5,
                label=f"Anomaly Threshold ({percentile}° Perc) = {threshold:.2f}")

    plt.title(f"KDE Plot (W = {window_size}s)", fontweight="bold", pad=15)
    plt.xlabel("Anomaly Score (MSE_norm + Dist_norm)", fontweight="bold")
    plt.ylabel("Probability Density", fontweight="bold")

    plt.legend(shadow=True, loc='upper right')
    plt.tight_layout()

    filename = f"KDE_W{window_size}s.png"
    plt.savefig(filename, dpi=300)
    print(f"[+] Grafico salvato: '{filename}'")


def plot_confusion_matrix(labels, scores, threshold, window_size):
    """
    Evaluates predictions against ground truth and generates a styled Confusion Matrix.
    Uses a single-tail classification strategy (Out-of-Bound detection).
    """
    print("\n[*] Generating Confusion Matrix...")

    # Single-tail classification: Any score strictly greater than the threshold is marked as an anomaly (1)
    preds = (scores > threshold).astype(int)
    cm = confusion_matrix(labels, preds)

    # Initialize the heatmap visual
    plt.figure(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", cbar=False,
                xticklabels=["Benign (0)", "Attack (1)"],
                yticklabels=["Benign (0)", "Attack (1)"])
    plt.title(f"Confusion Matrix (W = {window_size}s)", fontweight="bold", pad=15)
    plt.xlabel("Predicted Label", fontweight="bold")
    plt.ylabel("Ground Truth", fontweight="bold")
    plt.tight_layout()

    filename = f"CM_W{window_size}s.png"
    plt.savefig(filename, dpi=300)
    print(f"[+] Plot saved: '{filename}'")

    # Print analytical results to console
    tn, fp, fn, tp = cm.ravel()
    print(f"    -> True Negatives (Legitimate traffic allowed): {tn}")
    print(f"    -> False Positives (False alarms generated): {fp}")
    print(f"    -> False Negatives (Attacks missed): {fn}")
    print(f"    -> True Positives (Attacks correctly blocked): {tp}")
=======
import os
import random
import numpy as np
import torch
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import confusion_matrix

def set_seed(seed=42):
    """
    Sets the random seed to ensure full reproducibility.
    Disables non-deterministic GPU optimizations.
    """
    # Python and OS-level Seed
    random.seed(seed)
    os.environ['PYTHONHASHSEED'] = str(seed)

    # NumPy seed for data manipulation
    np.random.seed(seed)

    # PyTorch seeds for CPU and GPU operations
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)

    # Enforce strict CUDA determinism (disables auto-tuning optimizations)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


class EarlyStopping:
    """
    Halts training if validation loss stops improving to prevent overfitting.
    """
    def __init__(self, patience, path='best_saint.pth'):
        self.patience, self.path = patience, path
        self.counter, self.best_loss, self.early_stop = 0, None, False

    def __call__(self, val_loss, model):
        """
        Evaluates the current validation loss against the historical best.
        Saves the model state if an improvement is detected.
        """
        if self.best_loss is None or val_loss < self.best_loss:
            # Improvement detected: save weights and reset patience counter
            self.best_loss = val_loss
            torch.save(model.state_dict(), self.path)
            self.counter = 0
        else:
            # No improvement: increment counter and check stopping condition
            self.counter += 1
            if self.counter >= self.patience:
                self.early_stop = True


def plot_kde_distribution(val_scores, test_scores, test_labels, threshold, percentile, window_size):
    """
    Generates and saves a Kernel Density Estimation (KDE) plot of the anomaly scores.
    Visually demonstrates the separation between benign traffic and malicious traffic,
    while mapping the unsupervised threshold.
    """
    print(f"\n[*] Generating KDE Plot (W={window_size}s)...")
    sns.set_theme(style="whitegrid", context="paper", font_scale=1.2)
    plt.figure(figsize=(10, 5))

    # Plot the baseline physiological distribution (Validation Set)
    sns.kdeplot(val_scores, fill=True, color="#3182ce", label="Benign Traffic", alpha=0.6)

    # Filter and plot the malicious score distribution from the Test Set
    attack_scores = test_scores[test_labels == 1]
    if len(attack_scores) > 0:
        sns.kdeplot(attack_scores, fill=True, color="#e53e3e", label="Malicious Traffic", alpha=0.6)

    # Plot the single upper-bound anomaly threshold
    plt.axvline(threshold, color="#1a202c", linestyle="--", linewidth=2.5,
                label=f"Anomaly Threshold ({percentile}° Perc) = {threshold:.2f}")

    plt.title(f"KDE Plot (W = {window_size}s)", fontweight="bold", pad=15)
    plt.xlabel("Anomaly Score (MSE_norm + Dist_norm)", fontweight="bold")
    plt.ylabel("Probability Density", fontweight="bold")

    plt.legend(shadow=True, loc='upper right')
    plt.tight_layout()

    filename = f"KDE_W{window_size}s.png"
    plt.savefig(filename, dpi=300)
    print(f"[+] Grafico salvato: '{filename}'")


def plot_confusion_matrix(labels, scores, threshold, window_size):
    """
    Evaluates predictions against ground truth and generates a styled Confusion Matrix.
    Uses a single-tail classification strategy (Out-of-Bound detection).
    """
    print("\n[*] Generating Confusion Matrix...")

    # Single-tail classification: Any score strictly greater than the threshold is marked as an anomaly (1)
    preds = (scores > threshold).astype(int)
    cm = confusion_matrix(labels, preds)

    # Initialize the heatmap visual
    plt.figure(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", cbar=False,
                xticklabels=["Benign (0)", "Attack (1)"],
                yticklabels=["Benign (0)", "Attack (1)"])
    plt.title(f"Confusion Matrix (W = {window_size}s)", fontweight="bold", pad=15)
    plt.xlabel("Predicted Label", fontweight="bold")
    plt.ylabel("Ground Truth", fontweight="bold")
    plt.tight_layout()

    filename = f"CM_W{window_size}s.png"
    plt.savefig(filename, dpi=300)
    print(f"[+] Plot saved: '{filename}'")

    # Print analytical results to console
    tn, fp, fn, tp = cm.ravel()
    print(f"    -> True Negatives (Legitimate traffic allowed): {tn}")
    print(f"    -> False Positives (False alarms generated): {fp}")
    print(f"    -> False Negatives (Attacks missed): {fn}")
    print(f"    -> True Positives (Attacks correctly blocked): {tp}")
>>>>>>> ffcacd5028658b79102cd438e59c1bb21b886285
