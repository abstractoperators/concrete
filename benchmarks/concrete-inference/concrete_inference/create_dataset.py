# Create dataset from existing swe-bench huggingface dataset

# 1. Verified dataset + join for oracle and bm context
# 2. random or selected split
# 3. Own context
# 4. Should be able to update/augment existing dataset w/ context

# 5. Basal dataset should not include any context.
# 6. Utility for adding context to dataset (via oracle or bm context) should be possible.

import argparse
from pathlib import Path

from datasets import Dataset, DatasetDict, load_dataset

from concrete.clients import CLIClient


def download_dataset(
    dataset_name: str = "princeton-nlp/SWE-bench_oracle/test",
    revision: str = None,
    split: str = 'test',
):
    """
    Downloads a dataset from huggingface and saves it to the specified directory.

    Args:
        dataset_name (str): Name of the dataset to download. Defaults to "princeton-nlp/SWE-bench_oracle".
        revision (str): Revision of the dataset to download. Defaults to None.
        split (str): Split of the dataset to download. Official SWE-Bench splits use test split.
    """

    script_dir = Path(__file__).parent

    save_dir = script_dir.joinpath('datasets', dataset_name)
    dataset: Dataset = load_dataset(dataset_name, revision=revision, split=split)

    dataset.save_to_disk(save_dir)

    CLIClient.emit(f'{dataset_name}.{split} downloaded to {save_dir}')


def random_split(
    split_ratio: float,
    from_dataset_path: str,
    custom_split_name: str,
):
    """
    Randomly splits a dataset and saves the split to the specified directory.

    Args:
        split_ratio (float): How much of the dataset to keep.
        from_dataset_path (str): Path to the dataset to split.
        custom_split_name (str): Name of the split.
    """
    dataset = Dataset.load_from_disk(from_dataset_path)

    random_split = dataset.train_test_split(test_size=1 - split_ratio)

    subset = random_split["train"]

    save_path = f"{from_dataset_path}_{custom_split_name}"
    subset.save_to_disk(save_path)

    CLIClient.emit(f"Saved {custom_split_name} split to {save_path}")


def selected_split(
    from_dataset_path: str,
    custom_split_column: str,
    custom_split_values: list[str],
    custom_split_name: str,
):
    """
    Splits a dataset based on a custom column and equality values and saves the split to the specified directory.

    Args:
        from_dataset_path (str): Path to the dataset to split.
        custom_split_column (str): Column to split on.
        custom_split_values (list[str]): Values to split on.
        custom_split_name (str): Name of the split.
    """
    if not custom_split_values:
        custom_split_values = [  # Easy values from verified dataset
            'django__django-15103',
            'sympy__sympy-19346',
            'django__django-16662',
            'pytest-dev__pytest-7205',
            'pydata__xarray-3304',
        ]
    dataset = Dataset.load_from_disk(from_dataset_path)

    subset = dataset.filter(lambda row: row[custom_split_column] in custom_split_values)

    dataset_dict = DatasetDict({'test': subset})
    save_path = f"{from_dataset_path}_{custom_split_name}"
    dataset_dict.save_to_disk(save_path)

    CLIClient.emit(f"Saved {custom_split_name} split to {save_path}")


if __name__ == '__main__':
    # Should be able to download a dataset
    # Should be able to augment an existing dataset
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='subcommand')

    download_dataset_parser = subparsers.add_parser('download_dataset', help='Download a dataset from huggingface.')

    download_dataset_parser.add_argument(
        '--save_dir', type=str, default='datasets', help='Directory to save the dataset to.'
    )
    download_dataset_parser.add_argument(
        '--dataset_name', type=str, default='princeton-nlp/SWE-bench_oracle', help='Name of the dataset to download.'
    )
    download_dataset_parser.add_argument(
        '--revision', type=str, default=None, help='Revision of the dataset to download.'
    )

    random_split_parser = subparsers.add_parser('random_split', help='Randomly split a dataset.')
    random_split_parser.add_argument('--split_ratio', type=float, default=0.01, help='How much of the dataset to keep.')
    random_split_parser.add_argument('--from_dataset_path', type=str, help='Path to the dataset to split.')
    random_split_parser.add_argument('--custom_split_name', type=str, help='Name of the split')

    custom_split_parser = subparsers.add_parser('selected_split', help='Split a dataset based on a custom column.')
    custom_split_parser.add_argument('dataset_path', type=str)
    custom_split_parser.add_argument('split_column', type=str, help='Column to split on.')
    custom_split_parser.add_argument('split_name', type=str, help='Name of the split. Defaults to "custom_split".')
    custom_split_parser.add_argument(
        '--split_values', type=str, nargs='+', help='Values to split on (space-separated).'
    )

    args = parser.parse_args()

    if args.subcommand == 'download_dataset':
        download_dataset(
            dataset_name=args.dataset_name,
            revision=args.revision,
        )
    elif args.subcommand == 'random_split':
        random_split(
            split_ratio=args.split_ratio,
            from_dataset_path=args.from_dataset_path,
            custom_split_name=args.custom_split_name,
        )
    elif args.subcommand == 'selected_split':
        selected_split(
            from_dataset_path=args.dataset_path,
            custom_split_column=args.split_column,
            custom_split_values=args.split_values,
            custom_split_name=args.split_name,
        )
