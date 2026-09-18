"""Pre-aggregated facts the HTML report re-aggregates in the browser.

The report lets a reader narrow to stores, regions and a date range without
re-running the pipeline. To keep one definition of every KPI, Python computes the
measures per row and groups them to the finest grain the report needs; the page
only ever sums, subtracts, averages and divides those measures. No KPI formula is
restated in JavaScript, so a filtered figure equals the figure the pipeline would
produce for the same selection.

Where a rule rather than a formula decides grouping, the payload carries the answer
too: ``weeks_by_day`` holds the Monday ``enrich_sales`` assigned to each day, so the
page never works a week boundary out for itself.

Every measure here is additive over the grain it is stored at, except
``inventory_value``, which is averaged over weeks exactly as
``kpis.inventory.inventory_turnover`` averages it.
"""

import json

import pandas as pd

from retail_analytics.kpis.returns import RETURNS_RULE_ID

SALES_GRAIN = ["store_id", "article_id", "day"]


def build_facts(
    enriched_sales: pd.DataFrame,
    inventory: pd.DataFrame,
    articles: pd.DataFrame,
    stores: pd.DataFrame,
    *,
    sales_vs_inventory: pd.DataFrame,
    quarantined_sales: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """Group the run's rows to the grains the report re-aggregates from.

    Args:
        enriched_sales (pd.DataFrame): Sales with ``revenue``, ``cost``, ``day`` and the
            article and store attributes, as ``kpis.sales.enrich_sales`` returns them.
        inventory (pd.DataFrame): Validated weekly snapshots with a parsed ``date``.
        articles (pd.DataFrame): Validated articles with ``purchase_price``.
        stores (pd.DataFrame): Validated stores with ``store_name`` and ``region``.
        sales_vs_inventory (pd.DataFrame): The per-store, per-week comparison table.
        quarantined_sales (pd.DataFrame): Quarantined transactions inside the selection,
            with a parsed ``date``.

    Returns:
        dict[str, pd.DataFrame]: Tables keyed ``sales``, ``weeks_by_day``,
            ``inventory``, ``reconcile``, ``returns``, ``stores`` and ``articles``.
    """
    sales = (
        enriched_sales.groupby(SALES_GRAIN, as_index=False)
        .agg(
            units=("quantity", "sum"),
            revenue=("revenue", "sum"),
            cost=("cost", "sum"),
            transactions=("transaction_id", "count"),
        )
        .sort_values(SALES_GRAIN, ignore_index=True)
    )
    return {
        "sales": sales,
        "weeks_by_day": _weeks_by_day(enriched_sales),
        "inventory": _inventory_weeks(inventory, articles),
        "reconcile": sales_vs_inventory,
        "returns": _returns_days(quarantined_sales),
        "stores": stores[["store_id", "store_name", "region"]].sort_values(
            "store_id", ignore_index=True
        ),
        "articles": articles[["article_id", "article_name", "category"]].sort_values(
            "article_id", ignore_index=True
        ),
    }


def _weeks_by_day(enriched_sales: pd.DataFrame) -> pd.DataFrame:
    """Map each day in the data to the Monday starting its week.

    ``enrich_sales`` decides where a week begins. The page groups by week too, so it
    reads that decision from here instead of restating it in JavaScript, where it
    could drift.

    Args:
        enriched_sales (pd.DataFrame): Sales with ``day`` and ``week``, as
            ``kpis.sales.enrich_sales`` returns them.

    Returns:
        pd.DataFrame: One row per day with ``day`` and ``week``, ordered by day.
    """
    pairs = enriched_sales[["day", "week"]].drop_duplicates()
    return pairs.sort_values("day", ignore_index=True)


def _returns_days(quarantined_sales: pd.DataFrame) -> pd.DataFrame:
    """Total possible returns per store and day.

    Applies the same rule and value formula as ``kpis.returns.summarise_possible_returns``
    so the page's tile matches the pipeline's for any selection.

    Args:
        quarantined_sales (pd.DataFrame): Quarantined transactions inside the selection,
            with ``rule_id``, ``quantity``, ``selling_price`` and ``discount_pct``.

    Returns:
        pd.DataFrame: One row per store and day with ``store_id``, ``day``,
            ``transactions``, ``units`` and ``value``; empty columns when nothing was
            quarantined for a non-positive quantity.
    """
    columns = ["store_id", "day", "transactions", "units", "value"]
    if quarantined_sales.empty:
        return pd.DataFrame(columns=columns)
    rows = quarantined_sales[quarantined_sales["rule_id"] == RETURNS_RULE_ID]
    if rows.empty:
        return pd.DataFrame(columns=columns)
    units = rows["quantity"].abs()
    rows = rows.assign(
        day=rows["date"].dt.normalize(),
        units=units,
        value=units * rows["selling_price"] * (1 - rows["discount_pct"] / 100),
    )
    return (
        rows.groupby(["store_id", "day"], as_index=False)
        .agg(transactions=("units", "size"), units=("units", "sum"), value=("value", "sum"))
        .sort_values(["store_id", "day"], ignore_index=True)
    )


def _inventory_weeks(inventory: pd.DataFrame, articles: pd.DataFrame) -> pd.DataFrame:
    """Total cost of goods sold and inventory value per store and week.

    Mirrors the weekly step of ``kpis.inventory.inventory_turnover`` without applying a
    date range, so the page can pick the weeks a selection covers.

    Args:
        inventory (pd.DataFrame): Validated weekly snapshots with a parsed ``date``.
        articles (pd.DataFrame): Validated articles with ``purchase_price``.

    Returns:
        pd.DataFrame: One row per store and week with ``store_id``, ``week``, ``cogs``
            and ``inventory_value``.
    """
    rows = inventory.merge(articles[["article_id", "purchase_price"]], on="article_id")
    rows = rows.assign(
        cogs=rows["sold_qty"] * rows["purchase_price"],
        inventory_value=(rows["opening_stock"] + rows["closing_stock"])
        / 2
        * rows["purchase_price"],
    )
    weekly = rows.groupby(["store_id", "date"], as_index=False)[["cogs", "inventory_value"]].sum()
    return weekly.rename(columns={"date": "week"}).sort_values(
        ["store_id", "week"], ignore_index=True
    )


def _first_day(facts: dict[str, pd.DataFrame]) -> pd.Timestamp:
    """Give the earliest day any fact touches.

    Every date in the payload is stored as a whole-day offset from this day, so it has
    to sit at or before the start of every week a fact belongs to.

    Args:
        facts (dict[str, pd.DataFrame]): Tables from ``build_facts``.

    Returns:
        pd.Timestamp: The earliest day, normalised to midnight.
    """
    starts = [
        facts["sales"]["day"],
        facts["weeks_by_day"]["week"],
        facts["inventory"]["week"],
        facts["reconcile"]["week"],
        facts["returns"]["day"],
    ]
    return pd.Timestamp(pd.concat([s for s in starts if len(s)]).min())


def date_bounds(facts: dict[str, pd.DataFrame]) -> tuple[str, str]:
    """Give the first and last day the report's date controls may be set to.

    The range has to cover every fact the page can show, not just the sales days: an
    inventory week only counts towards turnover when it lies entirely inside the range
    (ADR 0004), so the last day must reach the end of the last week, not the last sale.
    Otherwise the page's own full selection would drop a week that the server-rendered
    report included, and the two would disagree on turnover.

    Args:
        facts (dict[str, pd.DataFrame]): Tables from ``build_facts``.

    Returns:
        tuple[str, str]: First and last day as ``YYYY-MM-DD``; two empty strings when
            the selection holds no facts at all.
    """
    if facts["sales"].empty:
        return "", ""
    week_end = pd.Timedelta(days=6)
    covered = [
        facts["sales"]["day"],
        facts["returns"]["day"],
        facts["inventory"]["week"],
        facts["reconcile"]["week"],
    ]
    # The bounds span the days the facts cover, which is not the payload's origin: that
    # sits at or before the Monday of the first sale's week, which may precede the data.
    days = pd.concat([s for s in covered if len(s)])
    last = pd.concat([days, facts["inventory"]["week"] + week_end]).max()
    return (
        pd.Timestamp(days.min()).strftime("%Y-%m-%d"),
        pd.Timestamp(last).strftime("%Y-%m-%d"),
    )


def facts_json(facts: dict[str, pd.DataFrame], top_n: int, min_units: int) -> str:
    """Serialise the facts as the compact payload the page's filter engine reads.

    Stores and articles become index arrays, and dates become whole-day offsets from
    the first day of the data, so the payload stays small enough to inline. Measures
    keep full precision: rounding them here would round before summing, and over ten
    thousand rows that moved gross margin by a lira against the pipeline's figure.

    Args:
        facts (dict[str, pd.DataFrame]): Tables from ``build_facts``.
        top_n (int): How many articles the top and bottom lists show.
        min_units (int): Units an article needs before it enters the margin % lists.

    Returns:
        str: JSON, safe to embed in a ``<script type="application/json">`` tag.
    """
    sales, inventory, reconcile = facts["sales"], facts["inventory"], facts["reconcile"]
    store_ids = facts["stores"]["store_id"].tolist()
    article_ids = facts["articles"]["article_id"].tolist()
    store_index = {value: i for i, value in enumerate(store_ids)}
    article_index = {value: i for i, value in enumerate(article_ids)}

    returns = facts["returns"]
    weeks_by_day = facts["weeks_by_day"]
    origin = _first_day(facts)

    def offsets(column: pd.Series) -> list[int]:
        """Express a date column as whole days after the first day in the data.

        Args:
            column (pd.Series): A datetime column.

        Returns:
            list[int]: One offset per row.
        """
        return [int(value) for value in (column - origin).dt.days]

    payload = {
        "origin": origin.strftime("%Y-%m-%d"),
        "topN": top_n,
        "minUnits": min_units,
        # Day offset -> the offset of the Monday starting its week, from enrich_sales.
        "weekOf": dict(
            zip(offsets(weeks_by_day["day"]), offsets(weeks_by_day["week"]), strict=True)
        ),
        "stores": facts["stores"].to_dict("records"),
        "articles": facts["articles"].to_dict("records"),
        "sales": {
            "s": [store_index[v] for v in sales["store_id"]],
            "a": [article_index[v] for v in sales["article_id"]],
            "d": offsets(sales["day"]),
            "u": sales["units"].astype(int).tolist(),
            "r": [float(v) for v in sales["revenue"]],
            "c": [float(v) for v in sales["cost"]],
            "n": sales["transactions"].astype(int).tolist(),
        },
        "inventory": {
            "s": [store_index[v] for v in inventory["store_id"]],
            "w": offsets(inventory["week"]),
            "cogs": [float(v) for v in inventory["cogs"]],
            "value": [float(v) for v in inventory["inventory_value"]],
        },
        "returns": {
            "s": [store_index[v] for v in returns["store_id"]],
            "d": offsets(returns["day"]) if len(returns) else [],
            "n": returns["transactions"].astype(int).tolist(),
            "v": [float(v) for v in returns["value"]],
        },
        "reconcile": {
            "s": [store_index[v] for v in reconcile["store_id"]],
            "w": offsets(reconcile["week"]),
            "articles": reconcile["articles"].astype(int).tolist(),
            "sold": reconcile["inventory_sold_qty"].astype(int).tolist(),
            "units": reconcile["transaction_units"].astype(int).tolist(),
        },
    }
    return json.dumps(payload, separators=(",", ":"))
