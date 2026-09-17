"""Inventory KPIs from the weekly inventory snapshots.

Each snapshot row covers one store, article and week (the week starting on the
snapshot date). Snapshots sample different articles each week, and a week's
closing stock does not carry into the next week's opening stock, so every figure
takes cost of goods sold and stock levels from the same rows.
"""

from dataclasses import dataclass
from datetime import date

import pandas as pd

WEEK = pd.Timedelta(days=7)


@dataclass(frozen=True)
class TurnoverResult:
    by_store: pd.DataFrame
    weeks: list[pd.Timestamp]


def inventory_turnover(
    inventory: pd.DataFrame,
    articles: pd.DataFrame,
    date_from: date | None,
    date_to: date | None,
) -> TurnoverResult:
    """Compute inventory turnover per store for the period, not annualised.

    Turnover = cost of goods sold / average weekly inventory value. Cost of goods
    sold is ``sold_qty`` x purchase price; a week's inventory value is
    (opening + closing) / 2 x purchase price, summed over the week's rows, and the
    average is over the weeks the store has snapshots for. Only weeks lying entirely
    inside the date range are used.

    Args:
        inventory (pd.DataFrame): Validated weekly snapshots with a parsed ``date``.
        articles (pd.DataFrame): Validated articles with ``purchase_price``.
        date_from (date | None): First day of the period; None for no lower bound.
        date_to (date | None): Last day of the period; None for no upper bound.

    Returns:
        TurnoverResult: ``by_store`` with ``store_id``, ``weeks``, ``cogs``,
            ``avg_inventory_value`` and ``turnover``; and ``weeks``, the start dates of
            the weeks used, in order. Both are empty when no full week fits the range.
    """
    in_range = pd.Series(True, index=inventory.index)
    if date_from is not None:
        in_range &= inventory["date"] >= pd.Timestamp(date_from)
    if date_to is not None:
        in_range &= inventory["date"] + WEEK - pd.Timedelta(days=1) <= pd.Timestamp(date_to)
    rows = inventory[in_range].merge(articles[["article_id", "purchase_price"]], on="article_id")

    rows = rows.assign(
        cogs=rows["sold_qty"] * rows["purchase_price"],
        inventory_value=(rows["opening_stock"] + rows["closing_stock"])
        / 2
        * rows["purchase_price"],
    )
    weekly = rows.groupby(["store_id", "date"], as_index=False)[["cogs", "inventory_value"]].sum()
    by_store = weekly.groupby("store_id", as_index=False).agg(
        weeks=("date", "nunique"),
        cogs=("cogs", "sum"),
        avg_inventory_value=("inventory_value", "mean"),
    )
    by_store["turnover"] = by_store["cogs"] / by_store["avg_inventory_value"]
    return TurnoverResult(by_store=by_store, weeks=sorted(rows["date"].unique()))


def compare_sales_with_inventory(
    enriched_sales: pd.DataFrame, inventory: pd.DataFrame, weeks: list[pd.Timestamp]
) -> pd.DataFrame:
    """Compare units sold per the inventory file with units in the transactions.

    Only store-article pairs present in a week's inventory snapshot are counted on
    both sides, so the comparison is like for like even though inventory samples a
    subset of articles.

    Args:
        enriched_sales (pd.DataFrame): Sales with ``store_id``, ``article_id``, ``week``
            (Monday starting the week) and ``quantity``.
        inventory (pd.DataFrame): Validated weekly snapshots with a parsed ``date``.
        weeks (list[pd.Timestamp]): Week start dates to compare, e.g. the weeks used for
            turnover.

    Returns:
        pd.DataFrame: One row per store and week with ``articles`` (pairs in the
            snapshot), ``inventory_sold_qty``, ``transaction_units`` and ``difference``
            (transactions minus inventory), ordered by store and week.
    """
    key = ["store_id", "week", "article_id"]
    snapshot = inventory[inventory["date"].isin(weeks)].rename(columns={"date": "week"})
    units = enriched_sales.groupby(key, as_index=False)["quantity"].sum()
    paired = snapshot[[*key, "sold_qty"]].merge(units, on=key, how="left").fillna({"quantity": 0})

    comparison = paired.groupby(["store_id", "week"], as_index=False).agg(
        articles=("article_id", "nunique"),
        inventory_sold_qty=("sold_qty", "sum"),
        transaction_units=("quantity", "sum"),
    )
    comparison["transaction_units"] = comparison["transaction_units"].astype(int)
    comparison["difference"] = comparison["transaction_units"] - comparison["inventory_sold_qty"]
    return comparison.sort_values(["store_id", "week"], ignore_index=True)
