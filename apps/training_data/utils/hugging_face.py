
from io import StringIO
import numpy as np
import pandas as pd
from datasets import Dataset, DatasetDict, Audio
from huggingface_hub import login


# Hugging Face Split names
TRAIN = "train"
TEST = "test"
VAL = "val"


def split_dataframe(df, train_ratio, test_ratio, validate_ratio):
    if train_ratio + test_ratio + validate_ratio != 100:
        raise ValueError("Split ratios must sum to 100")

    n = len(df)
    # Ensure at least one row per split
    min_rows = 3
    if n < min_rows:
        raise ValueError(f"Need at least {min_rows} rows to split into train/test/val")

    # First assign one row to each split
    df['split'] = None
    indices = np.random.choice(df.index, size=3, replace=False)
    df.loc[indices[0], 'split'] = TRAIN
    df.loc[indices[1], 'split'] = TEST
    df.loc[indices[2], 'split'] = VAL

    # Distribute remaining rows according to ratios
    remaining_indices = df[df['split'].isna()].index
    remaining_ratios = [train_ratio / 100, test_ratio / 100, validate_ratio / 100]
    remaining_ratios = [r / sum(remaining_ratios) for r in remaining_ratios]

    df.loc[remaining_indices, 'split'] = np.random.choice(
        [TRAIN, TEST, VAL],
        size=len(remaining_indices),
        p=remaining_ratios
    )

    return df


def compile_dataset(csv_files, train_ratio=70, test_ratio=15, validate_ratio=15):
    """Compile training dataset from multiple CSV files"""
    try:
        if not isinstance(csv_files, (list, tuple)):
            csv_files = [csv_files]

        # Combine all CSV files
        dfs = []
        for csv_file in csv_files:
            csv_file.file.seek(0)  # Reset file pointer
            content = csv_file.file.read().decode('utf-8')
            df = pd.read_csv(StringIO(content))
            dfs.append(df)

        if not dfs:
            raise ValueError("No valid CSV data found")

        combined_df = pd.concat(dfs, ignore_index=True)
        combined_df = split_dataframe(combined_df, train_ratio, test_ratio, validate_ratio)
        return combined_df

    except Exception as e:
        import traceback
        raise Exception(f"Error compiling dataset: {str(e)}\n{traceback.format_exc()}")

def upload_to_huggingface(dataset, client_id):
    """Upload dataset to HuggingFace"""
    try:
        # Convert to HuggingFace dataset format
        splits = {}
        for split in [TRAIN, TEST, VAL]:
            split_data = dataset[dataset['split'] == split]
            splits[split] = Dataset.from_pandas(split_data)

        # Create dataset dictionary
        hf_dataset = DatasetDict(splits)

        # Add audio feature
        for split in hf_dataset.keys():
            hf_dataset[split] = hf_dataset[split].cast_column("AudioPath", Audio(sampling_rate=16000))
        # Upload to HuggingFace
        login(token="")  # This will use HF_TOKEN environment variable

        # TODO: channel naming is still TBD. email's aren't valid because repo names can't contain 
        # certain characters present in emails.
        hf_dataset.push_to_hub(f"{client_id}-Voice-Data")

        return True

    except Exception as e:
        raise Exception(f"Error uploading to HuggingFace: {str(e)}")