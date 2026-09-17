"""Validation rules for ``transactions.csv``."""

import pandas as pd

from retail_analytics.validation.base import RuleResult, Severity

KURUS_PER_LIRA = 100


class ConvertKurusToLira:
    rule_id = "TXN_CURRENCY_KRS"
    table = "transactions"
    severity = Severity.FIX
    description = "Prices recorded in kurus (KRS) are converted to lira (TRY): 100 KRS = 1 TRY."

    def apply(self, df: pd.DataFrame) -> RuleResult:
        """Convert kurus prices to lira.

        Args:
            df (pd.DataFrame): Transactions with ``selling_price`` and ``currency`` columns.

        Returns:
            RuleResult: All rows, KRS prices divided by 100 and relabelled TRY; the fixed
                count is the number of KRS rows.
        """
        is_kurus = df["currency"] == "KRS"
        out = df.copy()
        out.loc[is_kurus, "selling_price"] = out.loc[is_kurus, "selling_price"] / KURUS_PER_LIRA
        out.loc[is_kurus, "currency"] = "TRY"
        return RuleResult(data=out, fixed_count=int(is_kurus.sum()))


class RejectNonPositiveQuantity:
    rule_id = "TXN_QUANTITY_NON_POSITIVE"
    table = "transactions"
    severity = Severity.REJECT
    description = (
        "Quantity must be positive. Negative quantities may be returns, but nothing links "
        "them to an original sale, so they are quarantined and reported as possible returns."
    )

    def apply(self, df: pd.DataFrame) -> RuleResult:
        """Quarantine rows whose quantity is zero or negative.

        Args:
            df (pd.DataFrame): Transactions with an integer ``quantity`` column.

        Returns:
            RuleResult: Rows with positive quantity, and rejected rows with a ``reason``.
        """
        bad = df["quantity"] <= 0
        rejected = df[bad].assign(
            reason="quantity must be positive, got " + df["quantity"][bad].astype(str)
        )
        return RuleResult(data=df[~bad], rejected=rejected)
