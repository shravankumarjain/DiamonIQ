"""Parquet-based caching helpers."""
from pathlib import Path
import pandas as pd


def save_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False, compression="snappy")


def load_parquet(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Cache file not found: {path}")
    return pd.read_parquet(path)


def cache_exists(path: Path) -> bool:
    """
    True only if the file exists, is non-trivially sized, AND contains rows.
    Prevents stale 0-row parquet files from being served as valid cache.
    """
    if not path.exists():
        return False
    if path.stat().st_size < 512:
        return False
    try:
        import pyarrow.parquet as pq
        meta = pq.read_metadata(str(path))
        return meta.num_rows > 0
    except Exception:
        return path.stat().st_size > 2048