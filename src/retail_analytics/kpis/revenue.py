"""Revenue: total sales value after discounts, in TRY."""

import pandas as pd


def line_revenue(sales: pd.DataFrame) -> pd.Series:
    """Compute the revenue of each sale line.

    Args:
        sales (pd.DataFrame): Sales with ``quantity``, ``selling_price`` (TRY) and
            ``discount_pct`` (0-100) columns.

    Returns:
        pd.Series: Quantity x unit price x (1 - discount / 100), one value per row.
    """
    return sales["quantity"] * sales["selling_price"] * (1 - sales["discount_pct"] / 100)


def revenue_by(sales: pd.DataFrame, dimensions: list[str]) -> pd.DataFrame:
    """Sum revenue after discounts over the given dimensions.

    Args:
        sales (pd.DataFrame): Sales with ``quantity``, ``selling_price`` (TRY) and
            ``discount_pct`` columns, plus every column named in ``dimensions``.
        dimensions (list[str]): Columns to group by, e.g. ``["store_id"]``.

    Returns:
        pd.DataFrame: One row per combination of ``dimensions`` with a ``revenue`` column.
    """
    return (
        sales.assign(revenue=line_revenue(sales)).groupby(dimensions)["revenue"].sum().reset_index()
    )
