"""Sales KPIs: revenue and gross margin at any level of detail.

All monetary values are in TRY. Revenue is after discount. Cost uses each
article's current purchase price: the data has no cost history.
"""

import pandas as pd

ARTICLE_ATTRIBUTES = ["article_id", "article_name", "category", "sub_category", "brand"]
STORE_ATTRIBUTES = ["store_id", "store_name", "region"]


def enrich_sales(sales: pd.DataFrame, articles: pd.DataFrame, stores: pd.DataFrame) -> pd.DataFrame:
    """Add revenue, cost, time periods and article and store attributes to each sale line.

    Args:
        sales (pd.DataFrame): Validated sales with ``date``, ``store_id``, ``article_id``,
            ``quantity``, ``selling_price`` (TRY) and ``discount_pct`` (0-100).
        articles (pd.DataFrame): Validated articles with ``purchase_price`` and the
            descriptive columns in ``ARTICLE_ATTRIBUTES``.
        stores (pd.DataFrame): Validated stores with the columns in ``STORE_ATTRIBUTES``.

    Returns:
        pd.DataFrame: The sales rows in their original order, with ``revenue``, ``cost``,
            ``gross_margin``, ``day``, ``week`` (the Monday starting it), ``month`` and
            the article and store attributes added.
    """
    enriched = sales.merge(
        articles[[*ARTICLE_ATTRIBUTES, "purchase_price"]], on="article_id", how="left"
    ).merge(stores[STORE_ATTRIBUTES], on="store_id", how="left")
    enriched.index = sales.index

    revenue = (
        enriched["quantity"] * enriched["selling_price"] * (1 - enriched["discount_pct"] / 100)
    )
    cost = enriched["quantity"] * enriched["purchase_price"]
    day = enriched["date"].dt.normalize()
    return enriched.assign(
        revenue=revenue,
        cost=cost,
        gross_margin=revenue - cost,
        day=day,
        week=day - pd.to_timedelta(day.dt.weekday, unit="D"),
        month=day.dt.to_period("M").astype(str),
    )


def summarise_sales(enriched: pd.DataFrame, dimensions: list[str]) -> pd.DataFrame:
    """Total revenue, cost and gross margin per combination of dimensions.

    Args:
        enriched (pd.DataFrame): Output of ``enrich_sales``.
        dimensions (list[str]): Columns to group by, e.g. ``["store_id", "store_name"]``;
            an empty list gives a single total row.

    Returns:
        pd.DataFrame: One row per combination with ``transactions``, ``units``,
            ``revenue``, ``cost``, ``gross_margin`` and ``gross_margin_pct`` (a
            fraction: gross margin / revenue), sorted by revenue, highest first.
    """
    grouped = enriched.assign(_all=0).groupby(dimensions or ["_all"])
    summary = grouped.agg(
        transactions=("transaction_id", "count"),
        units=("quantity", "sum"),
        revenue=("revenue", "sum"),
        cost=("cost", "sum"),
    )
    summary["gross_margin"] = summary["revenue"] - summary["cost"]
    summary["gross_margin_pct"] = summary["gross_margin"] / summary["revenue"]
    summary = summary.sort_values("revenue", ascending=False)
    return summary.reset_index(drop=not dimensions)
