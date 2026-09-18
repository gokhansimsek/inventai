"""Profile `data/` independently of the pipeline, to check the report's figures.

The browser test in ``tests/test_report_filters.py`` asserts what the report shows
for a handful of selections. Those expected values must not come from the code they
check, so this script re-derives them from the raw CSVs, applying the cleaning rules
as ``docs/data-quality.md`` states them in prose, with its own pandas expressions.

It shares no code with ``retail_analytics`` beyond pandas itself. Run it with
``uv run python tools/profile_selections.py``; it prints one block per selection,
plus the row counts that ``docs/data-quality.md`` records.
"""

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parents[1] / "data"

# (name, store_ids, first day, last day) - the selections the browser test drives.
SELECTIONS = [
    ("the whole month", [], "2024-03-01", "2024-03-31"),
    ("one store", ["S-001"], "2024-03-01", "2024-03-31"),
    ("one week", [], "2024-03-04", "2024-03-10"),
    ("one store over two weeks", ["S-002"], "2024-03-11", "2024-03-24"),
]


def _read(name: str) -> pd.DataFrame:
    """Read one raw CSV as text, so no parsing happens before the rules run.

    Args:
        name (str): File stem under ``data/``, e.g. ``"transactions"``.

    Returns:
        pd.DataFrame: Every column as a string, missing values as empty strings.
    """
    return pd.read_csv(DATA_DIR / f"{name}.csv", dtype=str, keep_default_na=False)


def _parse_dates(text: pd.Series) -> pd.Series:
    """Read a date column that mixes ISO and day-first spellings.

    ``docs/data-quality.md``: 1,396 dates are ``DD-MM-YYYY`` and are read day-first,
    because many have a first part above 12 and none has a second part above 12.

    Args:
        text (pd.Series): The raw date strings.

    Returns:
        pd.Series: Parsed timestamps.
    """
    iso = pd.to_datetime(text, format="%Y-%m-%d", errors="coerce")
    day_first = pd.to_datetime(text, format="%d-%m-%Y", errors="coerce")
    return iso.fillna(day_first)


def _clean_transactions() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply the documented transaction rules, in the documented order.

    Fixes run first (duplicate removal, day-first dates, kurus prices, future dates),
    then the rejections (non-positive quantity, unknown store), exactly as
    ``docs/data-quality.md`` describes.

    Returns:
        tuple[pd.DataFrame, pd.DataFrame]: The clean rows and the rejected rows, both
            with ``date``, ``quantity``, ``selling_price`` and ``discount_pct`` typed.
    """
    raw = _read("transactions")
    stores = _read("stores")

    # "Exact copies of an earlier row | 138 | Reject | first copy kept."
    rows = raw.drop_duplicates(keep="first").copy()
    rows["quantity"] = rows["quantity"].astype(int)
    rows["selling_price"] = rows["selling_price"].astype(float)
    rows["discount_pct"] = rows["discount_pct"].astype(float)
    rows["date"] = _parse_dates(rows["date"])

    # "Prices in kurus (KRS) ... divided by 100."
    kurus = rows["currency"] == "KRS"
    rows.loc[kurus, "selling_price"] = rows.loc[kurus, "selling_price"] / 100

    # "Dates in the future (2027) ... each takes the date of the preceding id."
    rows["_seq"] = rows["transaction_id"].str.extract(r"(\d+)$")[0].astype(int)
    rows = rows.sort_values("_seq", ignore_index=True)
    rows.loc[rows["date"] > pd.Timestamp("2024-12-31"), "date"] = pd.NaT
    rows["date"] = rows["date"].ffill()

    # "Quantity zero or negative | 577 | Reject" and "Unknown store S-099 | 115 | Reject".
    unusable = (rows["quantity"] <= 0) | ~rows["store_id"].isin(set(stores["store_id"]))
    return rows[~unusable], rows[unusable]


def _priced(rows: pd.DataFrame, articles: pd.DataFrame) -> pd.DataFrame:
    """Add revenue and cost to transaction rows.

    Revenue is after discount; cost is at the article's purchase price.

    Args:
        rows (pd.DataFrame): Transactions with ``quantity``, ``selling_price`` and
            ``discount_pct``.
        articles (pd.DataFrame): Articles with ``article_id`` and ``purchase_price``.

    Returns:
        pd.DataFrame: The rows with ``revenue`` and ``cost`` added.
    """
    priced = rows.merge(articles[["article_id", "purchase_price"]], on="article_id", how="left")
    net = priced["selling_price"] * (1 - priced["discount_pct"] / 100)
    return priced.assign(
        revenue=priced["quantity"] * net,
        cost=priced["quantity"] * priced["purchase_price"].astype(float),
    )


def _within(rows: pd.DataFrame, stores: list[str], first: str, last: str) -> pd.DataFrame:
    """Keep the rows a selection covers.

    Args:
        rows (pd.DataFrame): Rows with ``date`` and ``store_id``.
        stores (list[str]): Store ids to keep; empty keeps every store.
        first (str): First day, ``YYYY-MM-DD``.
        last (str): Last day, ``YYYY-MM-DD``.

    Returns:
        pd.DataFrame: The matching rows.
    """
    keep = rows["date"].between(pd.Timestamp(first), pd.Timestamp(last) + pd.Timedelta(hours=23))
    if stores:
        keep &= rows["store_id"].isin(stores)
    return rows[keep]


def _by_period(window: pd.DataFrame, period: str) -> pd.DataFrame:
    """Total units, revenue and margin per week or per calendar month of a selection.

    The report groups the same rows both ways, so this re-derives the grouping from the
    transaction date rather than from anything the pipeline computed. A week is labelled
    by the Monday starting it, as ``docs/design-session.md`` settles.

    Args:
        window (pd.DataFrame): Priced rows inside a selection, with ``date``,
            ``quantity``, ``revenue`` and ``cost``.
        period (str): ``"week"`` or ``"month"``.

    Returns:
        pd.DataFrame: One row per period with ``period`` (``YYYY-MM-DD`` for a week,
            ``YYYY-MM`` for a month), ``units``, ``revenue``, ``margin`` and
            ``margin_pct``, earliest period first.
    """
    day = window["date"].dt.normalize()
    label = (
        (day - pd.to_timedelta(day.dt.weekday, unit="D")).dt.strftime("%Y-%m-%d")
        if period == "week"
        else day.dt.to_period("M").astype(str)
    )
    totals = (
        window.assign(period=label)
        .groupby("period", as_index=False)
        .agg(units=("quantity", "sum"), revenue=("revenue", "sum"), cost=("cost", "sum"))
    )
    totals["margin"] = totals["revenue"] - totals["cost"]
    totals["margin_pct"] = totals["margin"] / totals["revenue"]
    return totals.sort_values("period", ignore_index=True)


def _turnover(stores: list[str], first: str, last: str) -> pd.DataFrame:
    """Compute inventory turnover per store for a selection.

    ``docs/data-quality.md`` and ADR 0004: turnover comes from the inventory file
    alone. Only weeks lying entirely inside the range count.

    Args:
        stores (list[str]): Store ids to keep; empty keeps every store.
        first (str): First day of the range, ``YYYY-MM-DD``.
        last (str): Last day of the range, ``YYYY-MM-DD``.

    Returns:
        pd.DataFrame: ``store_id``, ``weeks``, ``cogs``, ``avg_value`` and ``turnover``,
            highest turnover first; empty when no whole week fits the range.
    """
    inventory = _read("inventory")
    articles = _read("articles")
    inventory["date"] = _parse_dates(inventory["date"])
    for column in ("opening_stock", "closing_stock", "sold_qty"):
        inventory[column] = inventory[column].astype(int)

    ends = inventory["date"] + pd.Timedelta(days=6)
    whole = inventory["date"].ge(pd.Timestamp(first)) & ends.le(pd.Timestamp(last))
    rows = inventory[whole]
    if stores:
        rows = rows[rows["store_id"].isin(stores)]
    if rows.empty:
        return pd.DataFrame(columns=["store_id", "weeks", "cogs", "avg_value", "turnover"])

    rows = rows.merge(articles[["article_id", "purchase_price"]], on="article_id")
    price = rows["purchase_price"].astype(float)
    rows = rows.assign(
        cogs=rows["sold_qty"] * price,
        value=(rows["opening_stock"] + rows["closing_stock"]) / 2 * price,
    )
    weekly = rows.groupby(["store_id", "date"], as_index=False)[["cogs", "value"]].sum()
    by_store = weekly.groupby("store_id", as_index=False).agg(
        weeks=("date", "nunique"), cogs=("cogs", "sum"), avg_value=("value", "mean")
    )
    by_store["turnover"] = by_store["cogs"] / by_store["avg_value"]
    return by_store.sort_values("turnover", ascending=False, ignore_index=True)


def main() -> None:
    """Print the row counts and the per-selection figures the report is checked against."""
    clean, rejected = _clean_transactions()
    articles = _read("articles")
    known_stores = set(_read("stores")["store_id"])
    sales = _priced(clean, articles)
    returned = rejected[rejected["quantity"] <= 0]

    # Rows for stores missing from stores.csv are excluded from possible returns too,
    # so every figure covers the same stores (docs/assumptions.md, "Sales"). One of the
    # non-positive rows is for the unknown store S-099; it is counted here separately
    # rather than dropped silently, because the profile must show what it leaves out.
    orphan = returned[~returned["store_id"].isin(known_stores)]
    returns = _priced(returned[returned["store_id"].isin(known_stores)], articles)

    raw_rows = len(_read("transactions"))
    duplicates = raw_rows - len(clean) - len(rejected)
    print(
        f"transactions: raw {raw_rows:,} = clean {len(clean):,}"
        f" + rejected {len(rejected) + duplicates:,}"
        f" (of which {duplicates:,} exact copies)"
    )
    print(f"non-positive rows excluded from possible returns (unknown store): {len(orphan)}")
    print()

    for name, stores, first, last in SELECTIONS:
        window = _within(sales, stores, first, last)
        revenue, cost = window["revenue"].sum(), window["cost"].sum()
        margin = revenue - cost
        returned = _within(returns, stores, first, last)
        print(f"{name} ({first} to {last}, stores={stores or 'all'})")
        print(f"  revenue    {revenue:>16,.0f}")
        print(f"  margin     {margin:>16,.0f}")
        print(f"  margin_pct {margin / revenue:>15.1%}")
        print(f"  units      {window['quantity'].sum():>16,}")
        print(f"  lines      {len(window):>16,}")
        print(f"  returns    {abs(returned['revenue'].sum()):>16,.0f}")
        for week in _by_period(window, "week").itertuples():
            print(
                f"  week       {week.period} units {week.units:>8,} "
                f"revenue {week.revenue:>14,.0f} margin_pct {week.margin_pct:>7.1%}"
            )
        for month in _by_period(window, "month").itertuples():
            print(
                f"  month      {month.period} units {month.units:>8,} "
                f"revenue {month.revenue:>14,.0f} margin {month.margin:>13,.0f} "
                f"margin_pct {month.margin_pct:>7.1%}"
            )
        turnover = _turnover(stores, first, last)
        if turnover.empty:
            print("  turnover   (no whole inventory week in range)")
        for row in turnover.itertuples():
            print(
                f"  turnover   {row.store_id} {row.turnover:>6.2f} "
                f"({row.weeks} weeks, cogs {row.cogs:,.0f}, avg {row.avg_value:,.0f})"
            )
        print()


if __name__ == "__main__":
    main()
