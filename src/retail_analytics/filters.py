"""Narrow the validated data to the stores the user asked for."""

import pandas as pd

from retail_analytics.config import Settings
from retail_analytics.errors import ConfigError


def filter_sales(sales: pd.DataFrame, stores: pd.DataFrame, settings: Settings) -> pd.DataFrame:
    """Keep only the sales for the stores requested in the settings.

    Args:
        sales (pd.DataFrame): Validated transactions.
        stores (pd.DataFrame): Validated store master data, used to check requested ids.
        settings (Settings): Run settings; an empty ``stores`` selection keeps every sale.

    Returns:
        pd.DataFrame: The sales rows for the requested stores.

    Raises:
        ConfigError: If a requested store id is not in the store master data.
    """
    if not settings.stores:
        return sales
    known = sorted(stores["store_id"])
    for store in settings.stores:
        if store not in known:
            raise ConfigError(f"Unknown store '{store}'. Valid stores: {', '.join(known)}")
    return sales[sales["store_id"].isin(settings.stores)]
