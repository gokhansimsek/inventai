"""Narrow validated sales to the stores, regions and dates the user asked for.

Filters run after validation, so the data-quality results always describe the
full input whatever is selected.
"""

import pandas as pd

from retail_analytics.config import Settings
from retail_analytics.errors import ConfigError


def filter_sales(sales: pd.DataFrame, stores: pd.DataFrame, settings: Settings) -> pd.DataFrame:
    """Keep only the sales matching the store, region and date selection.

    Args:
        sales (pd.DataFrame): Validated transactions with ``store_id`` and a parsed
            ``date``.
        stores (pd.DataFrame): Validated store master data with ``store_id`` and
            ``region``.
        settings (Settings): Run settings; empty selections keep everything.

    Returns:
        pd.DataFrame: The sales rows inside the selection.

    Raises:
        ConfigError: If a requested store or region does not exist.
    """
    selected = filter_by_store(sales, stores, settings)
    keep = pd.Series(True, index=selected.index)
    if settings.date_from:
        keep &= selected["date"] >= pd.Timestamp(settings.date_from)
    if settings.date_to:
        keep &= selected["date"] <= pd.Timestamp(settings.date_to)
    return selected[keep]


def filter_by_store(rows: pd.DataFrame, stores: pd.DataFrame, settings: Settings) -> pd.DataFrame:
    """Keep only rows belonging to known stores inside the store and region selection.

    Rows for stores missing from the master data are always dropped, so figures built
    from quarantined rows cover the same stores as revenue.

    Args:
        rows (pd.DataFrame): Any table with a ``store_id`` column.
        stores (pd.DataFrame): Validated store master data with ``store_id`` and
            ``region``.
        settings (Settings): Run settings; empty selections keep every known store.

    Returns:
        pd.DataFrame: The rows for the selected stores.

    Raises:
        ConfigError: If a requested store or region does not exist.
    """
    _check_known("store", settings.stores, stores["store_id"])
    _check_known("region", settings.regions, stores["region"])

    selected = stores
    if settings.stores:
        selected = selected[selected["store_id"].isin(settings.stores)]
    if settings.regions:
        selected = selected[selected["region"].isin(settings.regions)]
    return rows[rows["store_id"].isin(selected["store_id"])]


def _check_known(kind: str, requested: tuple[str, ...], known: pd.Series) -> None:
    """Raise if any requested value is not among the known ones.

    Args:
        kind (str): What the values are, for the message, e.g. ``"store"``.
        requested (tuple[str, ...]): Values the user asked for.
        known (pd.Series): Values that exist in the master data.

    Raises:
        ConfigError: Naming the first unknown value and listing the valid ones.
    """
    valid = sorted(set(known))
    for value in requested:
        if value not in valid:
            raise ConfigError(f"Unknown {kind} '{value}'. Valid {kind}s: {', '.join(valid)}")
