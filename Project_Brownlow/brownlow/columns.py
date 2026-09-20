"""Normalize scraped AFL Tables headers to the project's snake_case names."""

import pandas as pd

import config


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename known source/legacy columns. Unknown columns are left as-is."""
    mapping = {old: new for old, new in config.COLUMN_RENAME.items() if old in df.columns}
    return df.rename(columns=mapping)
