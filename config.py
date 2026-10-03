<<<<<<< HEAD
from dataclasses import dataclass, field
from typing import List


@dataclass
class Configurator:
    """ Centralized configuration class to manage all hyperparameters and architectural settings."""

    # Dataset path
    dataset_path = r"C:\Users\miche\OneDrive - Politecnico di Bari\Desktop\Poliba\Magistrale\Materiale Tesi\Github\5G-NIDD\BTS1_BTS2_fields_preserved.csv"

    # Global random seed to ensure deterministic behavior
    seed: int = 42

    # Data Processing and Memory Management
    max_seq_len: int = 256
    batch_size: int = 8
    window_sizes_seconds: List[int] = field(default_factory=lambda: [10])

    # Model Architecture
    embed_dim: int = 32
    num_encoders: int = 2
    dropout: float = 0.1

    # Training and Optimization Parameters
    epochs: int = 1
    lr: float = 1e-4
    weight_decay: float = 1e-3
    early_stop_patience: int = 7

    # Self-Supervised Learning (SSL) and Contrastive Learning Parameters
    temperature: float = 0.7
    mask_prob: float = 0.3
    contrastive_weight: float = 0.5

    # Confidence Interval
    threshold_percentile: float = 95.0

    def print_config(self):
        """Prints a formatted summary of the current active configuration."""
        print("\n" + "=" * 50)
        print("[*] EXPERIMENT CONFIGURATION")
        print("=" * 50)
        for k, v in self.__dict__.items():
            print(f"    -> {k.upper()}: {v}")
        print("=" * 50 + "\n")
=======
from dataclasses import dataclass, field
from typing import List


@dataclass
class Configurator:
    """ Centralized configuration class to manage all hyperparameters and architectural settings."""

    # Dataset path
    dataset_path = r"C:\Users\miche\OneDrive - Politecnico di Bari\Desktop\Poliba\Magistrale\Materiale Tesi\Github\5G-NIDD\BTS1_BTS2_fields_preserved.csv"

    # Global random seed to ensure deterministic behavior
    seed: int = 42

    # Data Processing and Memory Management
    max_seq_len: int = 256
    batch_size: int = 8
    window_sizes_seconds: List[int] = field(default_factory=lambda: [10])

    # Model Architecture
    embed_dim: int = 32
    num_encoders: int = 2
    dropout: float = 0.1

    # Training and Optimization Parameters
    epochs: int = 1
    lr: float = 1e-4
    weight_decay: float = 1e-3
    early_stop_patience: int = 7

    # Self-Supervised Learning (SSL) and Contrastive Learning Parameters
    temperature: float = 0.7
    mask_prob: float = 0.3
    contrastive_weight: float = 0.5

    # Confidence Interval
    threshold_percentile: float = 95.0

    def print_config(self):
        """Prints a formatted summary of the current active configuration."""
        print("\n" + "=" * 50)
        print("[*] EXPERIMENT CONFIGURATION")
        print("=" * 50)
        for k, v in self.__dict__.items():
            print(f"    -> {k.upper()}: {v}")
        print("=" * 50 + "\n")
>>>>>>> ffcacd5028658b79102cd438e59c1bb21b886285
