"""Top and bottom articles by revenue and gross margin."""

import pandas as pd

from retail_analytics.kpis.sales import summarise_sales

ARTICLE_COLUMNS = ["article_id", "article_name", "category"]


def rank_articles(
    enriched: pd.DataFrame, n: int, min_units_for_margin_pct: int
) -> dict[str, pd.DataFrame]:
    """Rank articles top and bottom by revenue, margin in TRY and margin percentage.

    Margin percentage alone favours articles that sold a handful of units, so the
    margin percentage lists only include articles with enough units sold.

    Args:
        enriched (pd.DataFrame): Output of ``enrich_sales``.
        n (int): How many articles each list holds.
        min_units_for_margin_pct (int): Minimum units sold for an article to appear in
            the margin percentage lists.

    Returns:
        dict[str, pd.DataFrame]: Six lists keyed ``top_by_revenue``,
            ``bottom_by_revenue``, ``top_by_margin_try``, ``bottom_by_margin_try``,
            ``top_by_margin_pct`` and ``bottom_by_margin_pct``. Each row has ``rank``
            (1 = first in that list), the article columns, units, revenue, cost,
            gross margin and gross margin percentage. Bottom lists start with the lowest.
    """
    totals = summarise_sales(enriched, ARTICLE_COLUMNS)
    eligible_for_pct = totals[totals["units"] >= min_units_for_margin_pct]
    measures = {
        "revenue": ("revenue", totals),
        "margin_try": ("gross_margin", totals),
        "margin_pct": ("gross_margin_pct", eligible_for_pct),
    }

    rankings = {}
    for name, (column, frame) in measures.items():
        rankings[f"top_by_{name}"] = _ranked(frame, column, n, highest_first=True)
        rankings[f"bottom_by_{name}"] = _ranked(frame, column, n, highest_first=False)
    return rankings


def _ranked(totals: pd.DataFrame, column: str, n: int, highest_first: bool) -> pd.DataFrame:
    """Take the first ``n`` articles ordered by one measure and number them.

    Args:
        totals (pd.DataFrame): One row per article.
        column (str): Measure to order by.
        n (int): How many rows to keep.
        highest_first (bool): True for a top list, False for a bottom list.

    Returns:
        pd.DataFrame: The first ``n`` rows with a ``rank`` column starting at 1.
    """
    ordered = totals.sort_values(column, ascending=not highest_first, kind="stable").head(n)
    return ordered.reset_index(drop=True).assign(rank=lambda df: df.index + 1)[
        ["rank", *[c for c in ordered.columns]]
    ]
