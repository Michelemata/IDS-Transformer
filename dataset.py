<<<<<<< HEAD
import pandas as pd
import numpy as np
import torch
from torch.utils.data import Dataset
from sklearn.preprocessing import OrdinalEncoder


class DataPreprocessor:
    """
    Handles data loading, cleaning, temporal sorting, and feature encoding
    for the network traffic dataset.
    """
    def __init__(self, file_path):
        self.file_path = file_path
        self.df = None
        self.scalers = {}
        self.label_encoders = {}

    def load_data(self):
        """Loads the raw CSV dataset into a Pandas DataFrame."""
        # low_memory=False prevents dtype guessing warnings on large, mixed-type columns
        self.df = pd.read_csv(self.file_path, low_memory=False)
        print(f"[+] Dataset loaded. Shape: {self.df.shape}")

    def feature_selection_and_cleaning(self):
        """
        Cleans the dataset by:
        1. Zero-filling missing values in critical protocol metrics.
        2. Dropping noisy columns with over 70% missing data.
        3. Removing isolated rows with missing critical headers (micro-anomalies).
        """
        print("[*] Starting Feature Selection and Data Cleaning...")

        # 1. Zero-fill missing values for specific TCP/IP protocol-related columns
        # In network traffic, a missing window or base sequence often implies a value of 0
        protocol_cols_to_fill = ['SrcWin', 'DstWin', 'SrcTCPBase', 'DstTCPBase', 'Sport', 'Dport']
        for col in protocol_cols_to_fill:
            if col in self.df.columns:
                self.df[col] = self.df[col].fillna(0.0)

        # 2. Drop columns with more than 70% missing values to reduce noise
        null_percentages = self.df.isnull().mean()
        cols_to_drop = null_percentages[null_percentages > 0.70].index.tolist()
        cols_to_drop = [c for c in cols_to_drop if c not in protocol_cols_to_fill]
        self.df = self.df.drop(columns=cols_to_drop)

        # 3. Drop specific rows with micro-anomalies (e.g., missing critical headers)
        cols_few_nulls = ['sTos', 'sDSb', 'sTtl', 'sHops', 'sIpId']
        existing_cols = [c for c in cols_few_nulls if c in self.df.columns]
        self.df = self.df.dropna(subset=existing_cols)

        # Final safety drop for any remaining NaNs to prevent PyTorch tensor errors
        self.df = self.df.dropna()

    def _parse_time_to_seconds(self, time_str):
        """Helper method to convert 'HH:MM:SS' or 'MM:SS' strings into total seconds."""
        try:
            parts = str(time_str).split(':')
            if len(parts) == 2:
                return int(parts[0]) * 60 + float(parts[1])
            elif len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
            return float(time_str)
        except:
            return 0.0

    def apply_temporal_windows(self, window_size_seconds):
        """
        Groups sequential network flows into discrete temporal windows
        and sorts them chronologically to simulate real-time stream ingestion.
        """
        print(f"[*] Ordinamento temporale (Finestra: {window_size_seconds}s)...")
        self.df['StartTime_sec'] = self.df['StartTime'].apply(self._parse_time_to_seconds)

        # Discretize time into window IDs based on the chosen window size
        self.df['Window_ID'] = (self.df['StartTime_sec'] // window_size_seconds).astype(int)

        # Sort chronologically by timestamp; break ties by sequence ID to preserve exact packet order
        self.df = self.df.sort_values(by=['StartTime_sec', 'Seq']).reset_index(drop=True)
        self.df = self.df.drop(columns=['StartTime_sec'])

    def encode_features(self):
        """
        Separates categorical/continuous features, drops metadata to prevent data leakage,
        and initializes an OrdinalEncoder resilient to unknown categorical values.
        """
        print("[*] Starting Encoding...")

        # Metadata and identifiers that must not be used as training features
        cols_to_ignore = ['StartTime', 'LastTime', 'Seq', 'Window_ID', 'Attack Type', 'Attack Tool']

        # Binarize labels: 0 for Benign, 1 for Attack
        if 'Label' in self.df.columns:
            self.df['Is_Attack'] = self.df['Label'].apply(lambda x: 0 if str(x).strip().lower() == 'benign' else 1)
            cols_to_ignore.append('Label')

        # Identify categorical columns explicitly and by data type
        string_cols = self.df.select_dtypes(include=['object']).columns.tolist()
        explicit_cats = ['Proto', 'State', 'Dir', 'Cause', 'Sport', 'Dport']
        self.categorical_cols = list(set(string_cols + explicit_cats))
        self.categorical_cols = [c for c in self.categorical_cols if c in self.df.columns and c not in cols_to_ignore]

        # Force string casting to prevent OrdinalEncoder 'mixed types' errors
        for col in self.categorical_cols:
            self.df[col] = self.df[col].astype(str)

        # Initialize encoder. Unknown categories encountered during testing will be mapped to -1
        self.ordinal_encoder = OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=-1)

        # Any column not categorical or ignored is treated as continuous
        self.continuous_cols = [c for c in self.df.columns if
                                c not in self.categorical_cols + cols_to_ignore + ['Is_Attack']]

        # Drop metadata columns (except Window_ID) to strictly prevent data leakage
        cols_to_drop = [c for c in cols_to_ignore if c != 'Window_ID' and c in self.df.columns]
        self.df = self.df.drop(columns=cols_to_drop)

        print(f"[+] Categorical Features: {len(self.categorical_cols)} | Continuous Features: {len(self.continuous_cols)}")



class TemporalWindowDataset(Dataset):
    """
    PyTorch Dataset that chunks temporal windows into fixed-length sequences
    and applies zero-padding to meet the Transformer's max_seq_len requirement.
    """
    def __init__(self, df, categorical_cols, continuous_cols, max_seq_len):
        # Reset index to guarantee safe array slicing mapping
        df = df.reset_index(drop=True)

        self.max_seq_len = max_seq_len
        self.x_cat = df[categorical_cols].values.astype(np.int64)
        self.x_cont = df[continuous_cols].values.astype(np.float32)
        self.y = df['Is_Attack'].values.astype(np.int64)

        # Pre-compute chunks: slice each temporal window into segments of max_seq_len
        grouped_windows = df.groupby('Window_ID').groups
        self.chunks = []
        for win_id, indices in grouped_windows.items():
            idx_array = indices.values
            for start_i in range(0, len(idx_array), max_seq_len):
                self.chunks.append(idx_array[start_i:min(start_i + max_seq_len, len(idx_array))])

    def __len__(self):
        """Returns the total number of sequence chunks available."""
        return len(self.chunks)

    def __getitem__(self, idx):
        """
        Retrieves a chunk, pads sequences shorter than max_seq_len with zeros,
        and generates an attention mask to ignore padded tokens.
        """
        chunk_idx = self.chunks[idx]
        actual_len = len(chunk_idx)

        # Extract genuine data from the arrays
        cat_seq = self.x_cat[chunk_idx]
        cont_seq = self.x_cont[chunk_idx]
        labels = self.y[chunk_idx]

        # Initialize zero-padded arrays and a boolean mask (True means "ignore token")
        pad_cat = np.zeros((self.max_seq_len, cat_seq.shape[1]), dtype=np.int64)
        pad_cont = np.zeros((self.max_seq_len, cont_seq.shape[1]), dtype=np.float32)
        padding_mask = np.ones(self.max_seq_len, dtype=bool)

        # Inject real data into the padded structures
        pad_cat[:actual_len, :] = cat_seq
        pad_cont[:actual_len, :] = cont_seq
        padding_mask[:actual_len] = False

        # Assign an anomaly label to the chunk if at least one attack packet is present
        chunk_label = np.max(labels) if actual_len > 0 else 0
        return (torch.tensor(pad_cat), torch.tensor(pad_cont),
                torch.tensor(padding_mask), torch.tensor(chunk_label))
=======
import pandas as pd
import numpy as np
import torch
from torch.utils.data import Dataset
from sklearn.preprocessing import OrdinalEncoder


class DataPreprocessor:
    """
    Handles data loading, cleaning, temporal sorting, and feature encoding
    for the network traffic dataset.
    """
    def __init__(self, file_path):
        self.file_path = file_path
        self.df = None
        self.scalers = {}
        self.label_encoders = {}

    def load_data(self):
        """Loads the raw CSV dataset into a Pandas DataFrame."""
        # low_memory=False prevents dtype guessing warnings on large, mixed-type columns
        self.df = pd.read_csv(self.file_path, low_memory=False)
        print(f"[+] Dataset loaded. Shape: {self.df.shape}")

    def feature_selection_and_cleaning(self):
        """
        Cleans the dataset by:
        1. Zero-filling missing values in critical protocol metrics.
        2. Dropping noisy columns with over 70% missing data.
        3. Removing isolated rows with missing critical headers (micro-anomalies).
        """
        print("[*] Starting Feature Selection and Data Cleaning...")

        # 1. Zero-fill missing values for specific TCP/IP protocol-related columns
        # In network traffic, a missing window or base sequence often implies a value of 0
        protocol_cols_to_fill = ['SrcWin', 'DstWin', 'SrcTCPBase', 'DstTCPBase', 'Sport', 'Dport']
        for col in protocol_cols_to_fill:
            if col in self.df.columns:
                self.df[col] = self.df[col].fillna(0.0)

        # 2. Drop columns with more than 70% missing values to reduce noise
        null_percentages = self.df.isnull().mean()
        cols_to_drop = null_percentages[null_percentages > 0.70].index.tolist()
        cols_to_drop = [c for c in cols_to_drop if c not in protocol_cols_to_fill]
        self.df = self.df.drop(columns=cols_to_drop)

        # 3. Drop specific rows with micro-anomalies (e.g., missing critical headers)
        cols_few_nulls = ['sTos', 'sDSb', 'sTtl', 'sHops', 'sIpId']
        existing_cols = [c for c in cols_few_nulls if c in self.df.columns]
        self.df = self.df.dropna(subset=existing_cols)

        # Final safety drop for any remaining NaNs to prevent PyTorch tensor errors
        self.df = self.df.dropna()

    def _parse_time_to_seconds(self, time_str):
        """Helper method to convert 'HH:MM:SS' or 'MM:SS' strings into total seconds."""
        try:
            parts = str(time_str).split(':')
            if len(parts) == 2:
                return int(parts[0]) * 60 + float(parts[1])
            elif len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
            return float(time_str)
        except:
            return 0.0

    def apply_temporal_windows(self, window_size_seconds):
        """
        Groups sequential network flows into discrete temporal windows
        and sorts them chronologically to simulate real-time stream ingestion.
        """
        print(f"[*] Ordinamento temporale (Finestra: {window_size_seconds}s)...")
        self.df['StartTime_sec'] = self.df['StartTime'].apply(self._parse_time_to_seconds)

        # Discretize time into window IDs based on the chosen window size
        self.df['Window_ID'] = (self.df['StartTime_sec'] // window_size_seconds).astype(int)

        # Sort chronologically by timestamp; break ties by sequence ID to preserve exact packet order
        self.df = self.df.sort_values(by=['StartTime_sec', 'Seq']).reset_index(drop=True)
        self.df = self.df.drop(columns=['StartTime_sec'])

    def encode_features(self):
        """
        Separates categorical/continuous features, drops metadata to prevent data leakage,
        and initializes an OrdinalEncoder resilient to unknown categorical values.
        """
        print("[*] Starting Encoding...")

        # Metadata and identifiers that must not be used as training features
        cols_to_ignore = ['StartTime', 'LastTime', 'Seq', 'Window_ID', 'Attack Type', 'Attack Tool']

        # Binarize labels: 0 for Benign, 1 for Attack
        if 'Label' in self.df.columns:
            self.df['Is_Attack'] = self.df['Label'].apply(lambda x: 0 if str(x).strip().lower() == 'benign' else 1)
            cols_to_ignore.append('Label')

        # Identify categorical columns explicitly and by data type
        string_cols = self.df.select_dtypes(include=['object']).columns.tolist()
        explicit_cats = ['Proto', 'State', 'Dir', 'Cause', 'Sport', 'Dport']
        self.categorical_cols = list(set(string_cols + explicit_cats))
        self.categorical_cols = [c for c in self.categorical_cols if c in self.df.columns and c not in cols_to_ignore]

        # Force string casting to prevent OrdinalEncoder 'mixed types' errors
        for col in self.categorical_cols:
            self.df[col] = self.df[col].astype(str)

        # Initialize encoder. Unknown categories encountered during testing will be mapped to -1
        self.ordinal_encoder = OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=-1)

        # Any column not categorical or ignored is treated as continuous
        self.continuous_cols = [c for c in self.df.columns if
                                c not in self.categorical_cols + cols_to_ignore + ['Is_Attack']]

        # Drop metadata columns (except Window_ID) to strictly prevent data leakage
        cols_to_drop = [c for c in cols_to_ignore if c != 'Window_ID' and c in self.df.columns]
        self.df = self.df.drop(columns=cols_to_drop)

        print(f"[+] Categorical Features: {len(self.categorical_cols)} | Continuous Features: {len(self.continuous_cols)}")



class TemporalWindowDataset(Dataset):
    """
    PyTorch Dataset that chunks temporal windows into fixed-length sequences
    and applies zero-padding to meet the Transformer's max_seq_len requirement.
    """
    def __init__(self, df, categorical_cols, continuous_cols, max_seq_len):
        # Reset index to guarantee safe array slicing mapping
        df = df.reset_index(drop=True)

        self.max_seq_len = max_seq_len
        self.x_cat = df[categorical_cols].values.astype(np.int64)
        self.x_cont = df[continuous_cols].values.astype(np.float32)
        self.y = df['Is_Attack'].values.astype(np.int64)

        # Pre-compute chunks: slice each temporal window into segments of max_seq_len
        grouped_windows = df.groupby('Window_ID').groups
        self.chunks = []
        for win_id, indices in grouped_windows.items():
            idx_array = indices.values
            for start_i in range(0, len(idx_array), max_seq_len):
                self.chunks.append(idx_array[start_i:min(start_i + max_seq_len, len(idx_array))])

    def __len__(self):
        """Returns the total number of sequence chunks available."""
        return len(self.chunks)

    def __getitem__(self, idx):
        """
        Retrieves a chunk, pads sequences shorter than max_seq_len with zeros,
        and generates an attention mask to ignore padded tokens.
        """
        chunk_idx = self.chunks[idx]
        actual_len = len(chunk_idx)

        # Extract genuine data from the arrays
        cat_seq = self.x_cat[chunk_idx]
        cont_seq = self.x_cont[chunk_idx]
        labels = self.y[chunk_idx]

        # Initialize zero-padded arrays and a boolean mask (True means "ignore token")
        pad_cat = np.zeros((self.max_seq_len, cat_seq.shape[1]), dtype=np.int64)
        pad_cont = np.zeros((self.max_seq_len, cont_seq.shape[1]), dtype=np.float32)
        padding_mask = np.ones(self.max_seq_len, dtype=bool)

        # Inject real data into the padded structures
        pad_cat[:actual_len, :] = cat_seq
        pad_cont[:actual_len, :] = cont_seq
        padding_mask[:actual_len] = False

        # Assign an anomaly label to the chunk if at least one attack packet is present
        chunk_label = np.max(labels) if actual_len > 0 else 0
        return (torch.tensor(pad_cat), torch.tensor(pad_cont),
                torch.tensor(padding_mask), torch.tensor(chunk_label))
>>>>>>> ffcacd5028658b79102cd438e59c1bb21b886285
