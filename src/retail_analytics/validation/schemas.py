"""Column types for each table, and the rule that enforces them.

Dates stay as text here: the transactions file mixes date formats, and
parsing them is a dedicated fix rule, not a type coercion.
"""

import pandas as pd
import pandera.pandas as pa

from retail_analytics.errors import InputDataError
from retail_analytics.validation.base import RuleResult, Severity

SCHEMAS: dict[str, pa.DataFrameSchema] = {
    "stores": pa.DataFrameSchema(
        {
            "store_id": pa.Column(str),
            "store_name": pa.Column(str),
            "city": pa.Column(str),
            "region": pa.Column(str),
            "store_type": pa.Column(str),
            "opening_date": pa.Column(str),
            "area_sqft": pa.Column(int),
        },
        coerce=True,
    ),
    "articles": pa.DataFrameSchema(
        {
            "article_id": pa.Column(str),
            "article_name": pa.Column(str),
            "category": pa.Column(str),
            "sub_category": pa.Column(str),
            "brand": pa.Column(str),
            "purchase_price": pa.Column(float),
            "recommended_selling_price": pa.Column(float),
        },
        coerce=True,
    ),
    "transactions": pa.DataFrameSchema(
        {
            "transaction_id": pa.Column(str),
            "date": pa.Column(str),
            "store_id": pa.Column(str),
            "article_id": pa.Column(str),
            "quantity": pa.Column(int),
            "selling_price": pa.Column(float),
            "currency": pa.Column(str),
            "discount_pct": pa.Column(float),
            "customer_id": pa.Column(str),
            "weather_condition": pa.Column(str),
        },
        coerce=True,
    ),
    "inventory": pa.DataFrameSchema(
        {
            "date": pa.Column(str),
            "store_id": pa.Column(str),
            "article_id": pa.Column(str),
            "opening_stock": pa.Column(int),
            "received_qty": pa.Column(int),
            "sold_qty": pa.Column(int),
            "closing_stock": pa.Column(int),
        },
        coerce=True,
    ),
}


class CoerceToSchema:
    """Convert text columns to their types; quarantine rows whose values won't convert.

    A missing column is not a row problem: it breaks every row, so it stops the run.
    """

    severity = Severity.REJECT

    def __init__(self, table: str) -> None:
        """Build the type-coercion rule for one table.

        Args:
            table (str): Table name; must be a key of ``SCHEMAS``.
        """
        self.table = table
        self.rule_id = f"{table.upper()}_TYPES"
        self.description = f"Every {table} value must parse as its column type."
        self._schema = SCHEMAS[table]

    def apply(self, df: pd.DataFrame) -> RuleResult:
        """Convert text columns to their types, quarantining rows that fail to convert.

        Args:
            df (pd.DataFrame): The raw table, every column as ``str``.

        Returns:
            RuleResult: Typed rows that parsed, and rejected rows with a ``reason`` naming
                each column that failed.

        Raises:
            InputDataError: If a required column is missing.
        """
        try:
            return RuleResult(data=self._schema.validate(df, lazy=True))
        except pa.errors.SchemaErrors as exc:
            failures = exc.failure_cases

        table_level = failures[failures["index"].isna()]
        if not table_level.empty:
            problems = ", ".join(f"{c.check} {c.failure_case}" for c in table_level.itertuples())
            raise InputDataError(f"{self.table}: {problems}") from None

        row_level = failures[failures["check"].astype(str).str.startswith("coerce_dtype")]
        reasons = (
            row_level.assign(
                reason=row_level["column"]
                + ": cannot parse "
                + row_level["failure_case"].astype(str).map(repr)
            )
            .groupby("index")["reason"]
            .agg("; ".join)
        )
        bad = df.index.isin(reasons.index)
        rejected = df[bad].assign(reason=reasons)
        return RuleResult(data=self._schema.validate(df[~bad]), rejected=rejected)
