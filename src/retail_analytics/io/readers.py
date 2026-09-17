"""Read the raw CSV files.

Everything is read as text with no NA inference, so validation sees values
exactly as they appear in the file (e.g. ``"N/A"`` stays ``"N/A"``).
"""

from pathlib import Path

import pandas as pd

from retail_analytics.errors import InputDataError

TABLE_FILES = {
    "stores": "stores.csv",
    "articles": "articles.csv",
    "transactions": "transactions.csv",
    "inventory": "inventory.csv",
}


def load_raw_tables(data_dir: Path) -> dict[str, pd.DataFrame]:
    """Read every input CSV as text, exactly as it appears in the file.

    Args:
        data_dir (Path): Folder containing the input CSV files.

    Returns:
        dict[str, pd.DataFrame]: Table name (e.g. ``"transactions"``) mapped to its raw rows,
            every column as ``str``.

    Raises:
        InputDataError: If an expected file is missing.
    """
    tables = {}
    for table, filename in TABLE_FILES.items():
        path = data_dir / filename
        if not path.is_file():
            raise InputDataError(f"Input file not found: {path}")
        tables[table] = pd.read_csv(path, dtype=str, keep_default_na=False)
    return tables
