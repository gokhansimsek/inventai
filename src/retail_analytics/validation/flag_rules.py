"""Rules that flag suspicious rows for review while keeping them in the analysis."""

from collections.abc import Mapping

import pandas as pd

from retail_analytics.validation.base import RuleResult, Severity


class FlagInventoryImbalance:
    """Flag weekly inventory rows where the stock movement does not add up."""

    rule_id = "INVENTORY_STOCK_IMBALANCE"
    table = "inventory"
    severity = Severity.FLAG
    description = (
        "opening_stock + received_qty - sold_qty should equal closing_stock. Rows that do "
        "not balance are kept, using the reported stock levels, and flagged."
    )

    def apply(self, df: pd.DataFrame, tables: Mapping[str, pd.DataFrame]) -> RuleResult:
        """Flag rows whose stock movement does not balance.

        Args:
            df (pd.DataFrame): Inventory with integer stock columns.
            tables (Mapping[str, pd.DataFrame]): Other tables; unused.

        Returns:
            RuleResult: All rows, and flagged rows with a ``reason`` showing the arithmetic.
        """
        expected = df["opening_stock"] + df["received_qty"] - df["sold_qty"]
        off = expected != df["closing_stock"]
        rows = df[off]
        if rows.empty:
            return RuleResult(data=df)
        reason = (
            "opening "
            + rows["opening_stock"].astype(str)
            + " + received "
            + rows["received_qty"].astype(str)
            + " - sold "
            + rows["sold_qty"].astype(str)
            + " = "
            + expected[off].astype(str)
            + ", but closing is "
            + rows["closing_stock"].astype(str)
        )
        return RuleResult(data=df, flagged=rows.assign(reason=reason))


class FlagCostAboveRecommendedPrice:
    """Flag articles that cost more than their recommended selling price."""

    rule_id = "ARTICLES_COST_ABOVE_RECOMMENDED_PRICE"
    table = "articles"
    severity = Severity.FLAG
    description = (
        "An article whose purchase price is above its recommended selling price loses money "
        "on every sale at that price. It may be deliberate, so it is kept and flagged."
    )

    def apply(self, df: pd.DataFrame, tables: Mapping[str, pd.DataFrame]) -> RuleResult:
        """Flag articles priced below cost.

        Args:
            df (pd.DataFrame): Articles with ``purchase_price`` and
                ``recommended_selling_price``.
            tables (Mapping[str, pd.DataFrame]): Other tables; unused.

        Returns:
            RuleResult: All rows, and flagged rows with a ``reason``.
        """
        rows = df[df["purchase_price"] > df["recommended_selling_price"]]
        if rows.empty:
            return RuleResult(data=df)
        reason = (
            "purchase_price "
            + rows["purchase_price"].map("{:.2f}".format)
            + " is above recommended_selling_price "
            + rows["recommended_selling_price"].map("{:.2f}".format)
        )
        return RuleResult(data=df, flagged=rows.assign(reason=reason))


class FlagFutureDates:
    """Flag dates after the run date in a column no KPI depends on."""

    severity = Severity.FLAG

    def __init__(self, table: str, column: str, as_of: pd.Timestamp) -> None:
        """Build the rule for one date column.

        Args:
            table (str): Table to check.
            column (str): Parsed date column.
            as_of (pd.Timestamp): Latest possible date; later dates are in the future.
        """
        self.table = table
        self.column = column
        self.as_of = as_of
        self.rule_id = f"{table.upper()}_{column.upper()}_IN_FUTURE"
        self.description = (
            f"{table}.{column} after the run date is impossible. No KPI uses it, so the row "
            "is kept and flagged."
        )

    def apply(self, df: pd.DataFrame, tables: Mapping[str, pd.DataFrame]) -> RuleResult:
        """Flag rows dated after the run date.

        Args:
            df (pd.DataFrame): The table with a parsed date column.
            tables (Mapping[str, pd.DataFrame]): Other tables; unused.

        Returns:
            RuleResult: All rows, and flagged rows with a ``reason``.
        """
        rows = df[df[self.column] > self.as_of]
        if rows.empty:
            return RuleResult(data=df)
        reason = (
            f"{self.column} "
            + rows[self.column].dt.strftime("%Y-%m-%d")
            + f" is after the run date {self.as_of:%Y-%m-%d}"
        )
        return RuleResult(data=df, flagged=rows.assign(reason=reason))


class FlagPriceFarFromRecommended:
    """Flag sales whose price is far from the article's recommended price (outliers)."""

    rule_id = "TRANSACTIONS_PRICE_OUTLIER"
    table = "transactions"
    severity = Severity.FLAG

    def __init__(self, tolerance: float) -> None:
        """Build the rule.

        Args:
            tolerance (float): Allowed relative deviation from the recommended price,
                e.g. 0.5 flags prices below 50% or above 150% of it.
        """
        self.tolerance = tolerance
        self.description = (
            "A selling price more than "
            f"{tolerance:.0%} away from the article's recommended price suggests a unit or "
            "entry error. The sale is kept and flagged."
        )

    def apply(self, df: pd.DataFrame, tables: Mapping[str, pd.DataFrame]) -> RuleResult:
        """Flag sales priced outside the tolerance around the recommended price.

        Args:
            df (pd.DataFrame): Transactions with ``article_id`` and ``selling_price`` in TRY.
            tables (Mapping[str, pd.DataFrame]): Must contain ``articles`` with
                ``recommended_selling_price``.

        Returns:
            RuleResult: All rows, and flagged rows with a ``reason``.
        """
        recommended = df["article_id"].map(
            tables["articles"].set_index("article_id")["recommended_selling_price"]
        )
        deviation = df["selling_price"] / recommended - 1
        far = deviation.abs() > self.tolerance
        rows = df[far]
        if rows.empty:
            return RuleResult(data=df)
        direction = deviation[far].map(lambda d: "above" if d > 0 else "below")
        reason = (
            "selling_price "
            + rows["selling_price"].map("{:.2f}".format)
            + " is "
            + deviation[far].abs().map("{:.0%}".format)
            + " "
            + direction
            + " recommended "
            + recommended[far].map("{:.2f}".format)
        )
        return RuleResult(data=df, flagged=rows.assign(reason=reason))
