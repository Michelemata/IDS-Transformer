<<<<<<< HEAD
import warnings
import pandas as pd
import torch
from sklearn.preprocessing import StandardScaler
from config import Configurator
from utils import set_seed, plot_kde_distribution, plot_confusion_matrix
from dataset import DataPreprocessor
from training import train_ssl
from validation import calculate_unsupervised_threshold
from evaluation import run_evaluation

# Suppress warnings to maintain a clean console output during execution
warnings.filterwarnings('ignore')


if __name__ == "__main__":

    # Initialize Configuration
    config = Configurator()
    config.print_config()

    # Enforce reproducibility across CPU/GPU executions
    set_seed(config.seed)

    all_results = []

    # Benchmark Loop over different temporal windows
    for w in config.window_sizes_seconds:
        print("\n" + "=" * 60)
        print(f"[*] STARTING EXPERIMENT WITH TIME WINDOW: W = {w}s")
        print("=" * 60)

        # Re-initialize Preprocessor to prevent cross-window data leakage
        prep = DataPreprocessor(config.dataset_path)
        prep.load_data()
        prep.feature_selection_and_cleaning()

        # Group network flows into discrete time windows and encode features
        prep.apply_temporal_windows(window_size_seconds=w)
        prep.encode_features()
        df = prep.df

        # Isolate benign and malicious traffic for custom splitting logic
        df_benign = df[df['Is_Attack'] == 0].copy()
        df_attack = df[df['Is_Attack'] == 1].copy()

        # Split benign traffic (70% Train, 15% Val, 15% Test) to learn normal behavior patterns
        n_benign = len(df_benign)
        idx_train = int(n_benign * 0.70)
        idx_val = int(n_benign * 0.85)

        df_train_benign = df_benign.iloc[:idx_train].reset_index(drop=True)
        df_val_benign = df_benign.iloc[idx_train:idx_val].reset_index(drop=True)
        df_test_benign = df_benign.iloc[idx_val:].reset_index(drop=True)

        # Sequential Undersampling: Take a continuous chunk of attacks to match the benign test size
        # This ensures balanced evaluation metrics (50/50 Test Set)
        n_test_benign = len(df_test_benign)
        n_attacks_to_keep = min(n_test_benign, len(df_attack))
        df_attack_sampled = df_attack.iloc[:n_attacks_to_keep].reset_index(drop=True)

        # Build the final balanced Test Set
        df_test = pd.concat([df_test_benign, df_attack_sampled], ignore_index=True)

        # Sort chronologically to accurately simulate a real-world event stream
        df_test = df_test.sort_values(by=['Window_ID']).reset_index(drop=True)

        # Statistical and vocabulary isolation: Strict prevention of data leakage
        print("[*] Scaling continuous features...")
        scaler = StandardScaler()

        # Fit scaler strictly on the training set
        df_train_benign[prep.continuous_cols] = scaler.fit_transform(df_train_benign[prep.continuous_cols])

        # Apply transformations to Val/Test
        df_val_benign[prep.continuous_cols] = scaler.transform(df_val_benign[prep.continuous_cols])
        df_test[prep.continuous_cols] = scaler.transform(df_test[prep.continuous_cols])

        print("[*] Categorical Encoding (Handling Out-Of-Vocabulary)...")
        # Fit strictly on Train to learn only known physiological states/protocols
        df_train_benign[prep.categorical_cols] = prep.ordinal_encoder.fit_transform(
            df_train_benign[prep.categorical_cols])

        # # Safely transform Val/Test sets. Unseen categorical values will default to -1
        df_val_benign[prep.categorical_cols] = prep.ordinal_encoder.transform(df_val_benign[prep.categorical_cols])
        df_test[prep.categorical_cols] = prep.ordinal_encoder.transform(df_test[prep.categorical_cols])

        # Shift categorical indices by +1 to explicitly reserve index 0 for the <UNK> token
        for df_part in [df_train_benign, df_val_benign, df_test]:
            df_part[prep.categorical_cols] = df_part[prep.categorical_cols] + 1
            df_part[prep.categorical_cols] = df_part[prep.categorical_cols].astype(int)

        # Self-Supervised Training Phase
        model = train_ssl(
            df_train_benign, df_val_benign, prep.categorical_cols, prep.continuous_cols,
            prep.ordinal_encoder, config
        )

        # Hybrid Threshold Calculation Phase
        threshold, val_hybrid_scores, centroid, mse_params, dist_params = calculate_unsupervised_threshold(
            model, df_val_benign, prep.categorical_cols, prep.continuous_cols, config
        )

        # Inference Phase
        test_hybrid_scores, test_labels, auc, f1, precision, recall, accuracy, tn, fp, fn, tp, lat = run_evaluation(
            model, df_test, prep.categorical_cols, prep.continuous_cols,
            threshold, centroid, mse_params, dist_params, config
        )

        # Generate and save visual evidence of the experiment
        plot_kde_distribution(val_hybrid_scores, test_hybrid_scores, test_labels, threshold, config.threshold_percentile, window_size=w)
        plot_confusion_matrix(test_labels, test_hybrid_scores, threshold, window_size=w)

        # Append results for final reporting
        all_results.append({
            'Window_Size (s)': w,
            'AUC': round(auc, 4),
            'Accuracy': round(accuracy, 4),
            'Precision': round(precision, 4),
            'Recall': round(recall, 4),
            'F1_Score': round(f1, 4),
            'TP': int(tp),
            'FP': int(fp),
            'TN': int(tn),
            'FN': int(fn),
            'Latency (ms)': round(lat, 2)
        })

        # VRAM cleanup before the next window experiment
        del model, prep, df, df_train_benign, df_val_benign, df_test, df_test_benign, df_attack_sampled
        torch.cuda.empty_cache()

    # Display and export the final benchmark summary table
    print("\n" + "="*60)
    print("[!] Benchmark completed. Final results table:")
    print("="*60)
    df_results = pd.DataFrame(all_results)
    print(df_results.to_string(index=False))

    csv_filename = "Benchmark_Table.csv"
    df_results.to_csv(csv_filename, index=False)
    print(f"\n[+] CSV Table saved in '{csv_filename}'.")
=======
import warnings
import pandas as pd
import torch
from sklearn.preprocessing import StandardScaler
from config import Configurator
from utils import set_seed, plot_kde_distribution, plot_confusion_matrix
from dataset import DataPreprocessor
from training import train_ssl
from validation import calculate_unsupervised_threshold
from evaluation import run_evaluation

# Suppress warnings to maintain a clean console output during execution
warnings.filterwarnings('ignore')


if __name__ == "__main__":

    # Initialize Configuration
    config = Configurator()
    config.print_config()

    # Enforce reproducibility across CPU/GPU executions
    set_seed(config.seed)

    all_results = []

    # Benchmark Loop over different temporal windows
    for w in config.window_sizes_seconds:
        print("\n" + "=" * 60)
        print(f"[*] STARTING EXPERIMENT WITH TIME WINDOW: W = {w}s")
        print("=" * 60)

        # Re-initialize Preprocessor to prevent cross-window data leakage
        prep = DataPreprocessor(config.dataset_path)
        prep.load_data()
        prep.feature_selection_and_cleaning()

        # Group network flows into discrete time windows and encode features
        prep.apply_temporal_windows(window_size_seconds=w)
        prep.encode_features()
        df = prep.df

        # Isolate benign and malicious traffic for custom splitting logic
        df_benign = df[df['Is_Attack'] == 0].copy()
        df_attack = df[df['Is_Attack'] == 1].copy()

        # Split benign traffic (70% Train, 15% Val, 15% Test) to learn normal behavior patterns
        n_benign = len(df_benign)
        idx_train = int(n_benign * 0.70)
        idx_val = int(n_benign * 0.85)

        df_train_benign = df_benign.iloc[:idx_train].reset_index(drop=True)
        df_val_benign = df_benign.iloc[idx_train:idx_val].reset_index(drop=True)
        df_test_benign = df_benign.iloc[idx_val:].reset_index(drop=True)

        # Sequential Undersampling: Take a continuous chunk of attacks to match the benign test size
        # This ensures balanced evaluation metrics (50/50 Test Set)
        n_test_benign = len(df_test_benign)
        n_attacks_to_keep = min(n_test_benign, len(df_attack))
        df_attack_sampled = df_attack.iloc[:n_attacks_to_keep].reset_index(drop=True)

        # Build the final balanced Test Set
        df_test = pd.concat([df_test_benign, df_attack_sampled], ignore_index=True)

        # Sort chronologically to accurately simulate a real-world event stream
        df_test = df_test.sort_values(by=['Window_ID']).reset_index(drop=True)

        # Statistical and vocabulary isolation: Strict prevention of data leakage
        print("[*] Scaling continuous features...")
        scaler = StandardScaler()

        # Fit scaler strictly on the training set
        df_train_benign[prep.continuous_cols] = scaler.fit_transform(df_train_benign[prep.continuous_cols])

        # Apply transformations to Val/Test
        df_val_benign[prep.continuous_cols] = scaler.transform(df_val_benign[prep.continuous_cols])
        df_test[prep.continuous_cols] = scaler.transform(df_test[prep.continuous_cols])

        print("[*] Categorical Encoding (Handling Out-Of-Vocabulary)...")
        # Fit strictly on Train to learn only known physiological states/protocols
        df_train_benign[prep.categorical_cols] = prep.ordinal_encoder.fit_transform(
            df_train_benign[prep.categorical_cols])

        # # Safely transform Val/Test sets. Unseen categorical values will default to -1
        df_val_benign[prep.categorical_cols] = prep.ordinal_encoder.transform(df_val_benign[prep.categorical_cols])
        df_test[prep.categorical_cols] = prep.ordinal_encoder.transform(df_test[prep.categorical_cols])

        # Shift categorical indices by +1 to explicitly reserve index 0 for the <UNK> token
        for df_part in [df_train_benign, df_val_benign, df_test]:
            df_part[prep.categorical_cols] = df_part[prep.categorical_cols] + 1
            df_part[prep.categorical_cols] = df_part[prep.categorical_cols].astype(int)

        # Self-Supervised Training Phase
        model = train_ssl(
            df_train_benign, df_val_benign, prep.categorical_cols, prep.continuous_cols,
            prep.ordinal_encoder, config
        )

        # Hybrid Threshold Calculation Phase
        threshold, val_hybrid_scores, centroid, mse_params, dist_params = calculate_unsupervised_threshold(
            model, df_val_benign, prep.categorical_cols, prep.continuous_cols, config
        )

        # Inference Phase
        test_hybrid_scores, test_labels, auc, f1, precision, recall, accuracy, tn, fp, fn, tp, lat = run_evaluation(
            model, df_test, prep.categorical_cols, prep.continuous_cols,
            threshold, centroid, mse_params, dist_params, config
        )

        # Generate and save visual evidence of the experiment
        plot_kde_distribution(val_hybrid_scores, test_hybrid_scores, test_labels, threshold, config.threshold_percentile, window_size=w)
        plot_confusion_matrix(test_labels, test_hybrid_scores, threshold, window_size=w)

        # Append results for final reporting
        all_results.append({
            'Window_Size (s)': w,
            'AUC': round(auc, 4),
            'Accuracy': round(accuracy, 4),
            'Precision': round(precision, 4),
            'Recall': round(recall, 4),
            'F1_Score': round(f1, 4),
            'TP': int(tp),
            'FP': int(fp),
            'TN': int(tn),
            'FN': int(fn),
            'Latency (ms)': round(lat, 2)
        })

        # VRAM cleanup before the next window experiment
        del model, prep, df, df_train_benign, df_val_benign, df_test, df_test_benign, df_attack_sampled
        torch.cuda.empty_cache()

    # Display and export the final benchmark summary table
    print("\n" + "="*60)
    print("[!] Benchmark completed. Final results table:")
    print("="*60)
    df_results = pd.DataFrame(all_results)
    print(df_results.to_string(index=False))

    csv_filename = "Benchmark_Table.csv"
    df_results.to_csv(csv_filename, index=False)
    print(f"\n[+] CSV Table saved in '{csv_filename}'.")
>>>>>>> ffcacd5028658b79102cd438e59c1bb21b886285
