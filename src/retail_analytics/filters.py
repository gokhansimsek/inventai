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
    _check_known("store", settings.stores, stores["store_id"])
    _check_known("region", settings.regions, stores["region"])

    keep = pd.Series(True, index=sales.index)
    if settings.stores:
        keep &= sales["store_id"].isin(settings.stores)
    if settings.regions:
        in_regions = stores.loc[stores["region"].isin(settings.regions), "store_id"]
        keep &= sales["store_id"].isin(in_regions)
    if settings.date_from:
        keep &= sales["date"] >= pd.Timestamp(settings.date_from)
    if settings.date_to:
        keep &= sales["date"] <= pd.Timestamp(settings.date_to)
    return sales[keep]


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
