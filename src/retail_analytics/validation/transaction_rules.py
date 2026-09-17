"""Validation rules for ``transactions.csv``."""

from collections.abc import Mapping

import pandas as pd

from retail_analytics.validation.base import RuleResult, Severity

KURUS_PER_LIRA = 100


class ConvertKurusToLira:
    rule_id = "TRANSACTIONS_KRS_TO_TRY"
    table = "transactions"
    severity = Severity.FIX
    description = "Prices recorded in kurus (KRS) are converted to lira (TRY): 100 KRS = 1 TRY."

    def apply(self, df: pd.DataFrame, tables: Mapping[str, pd.DataFrame]) -> RuleResult:
        """Convert kurus prices to lira.

        Args:
            df (pd.DataFrame): Transactions with ``selling_price`` and ``currency`` columns.
            tables (Mapping[str, pd.DataFrame]): Other tables; unused.

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
    rule_id = "TRANSACTIONS_QUANTITY_NOT_POSITIVE"
    table = "transactions"
    severity = Severity.REJECT
    description = (
        "Quantity must be positive. Negative quantities may be returns, but nothing links "
        "them to an original sale, so they are quarantined and reported as possible returns."
    )

    def apply(self, df: pd.DataFrame, tables: Mapping[str, pd.DataFrame]) -> RuleResult:
        """Quarantine rows whose quantity is zero or negative.

        Args:
            df (pd.DataFrame): Transactions with an integer ``quantity`` column.
            tables (Mapping[str, pd.DataFrame]): Other tables; unused.

        Returns:
            RuleResult: Rows with positive quantity, and rejected rows with a ``reason``.
        """
        bad = df["quantity"] <= 0
        rejected = df[bad].assign(
            reason="quantity must be positive, got " + df["quantity"][bad].astype(str)
        )
        return RuleResult(data=df[~bad], rejected=rejected)


class InferFutureDatesFromIdOrder:
    """Date future transactions from their position in the transaction id sequence.

    In the data, transaction ids increase with date across every valid row, so a
    transaction with an impossible future date is given the date of the closest
    earlier id. The rule checks that ordering on the current data and quarantines
    future rows instead when it does not hold.
    """

    rule_id = "TRANSACTIONS_DATE_IN_FUTURE"
    table = "transactions"
    severity = Severity.FIX
    description = (
        "Dates after the run date are impossible. When transaction ids are in date order, "
        "such a row takes the date of the preceding transaction id and is flagged with its "
        "original date; otherwise it is quarantined."
    )

    def __init__(self, as_of: pd.Timestamp) -> None:
        """Build the rule.

        Args:
            as_of (pd.Timestamp): Latest possible date; later dates are in the future.
        """
        self.as_of = as_of

    def apply(self, df: pd.DataFrame, tables: Mapping[str, pd.DataFrame]) -> RuleResult:
        """Replace future dates using id order, or quarantine them.

        Args:
            df (pd.DataFrame): Transactions with ``transaction_id`` and a parsed ``date``.
            tables (Mapping[str, pd.DataFrame]): Other tables; unused.

        Returns:
            RuleResult: All rows with inferred dates in place, flagged rows carrying
                ``original_date`` and ``reason``; or, when ids are not in date order,
                the future rows rejected.
        """
        is_future = df["date"] > self.as_of
        if not is_future.any():
            return RuleResult(data=df)

        ordered = df.assign(_seq=df["transaction_id"].str.extract(r"(\d+)$")[0].astype(int))
        valid = ordered[~is_future].sort_values("_seq")
        if not valid["date"].is_monotonic_increasing:
            reason = (
                "future date, and transaction ids are not in date order so no date can be inferred"
            )
            return RuleResult(data=df[~is_future], rejected=df[is_future].assign(reason=reason))

        future = ordered[is_future].reset_index().sort_values("_seq")
        preceding = valid[["_seq", "transaction_id", "date"]].rename(
            columns={"transaction_id": "_preceding_id", "date": "_preceding_date"}
        )
        matched = pd.merge_asof(future, preceding, on="_seq", allow_exact_matches=False)
        matched = matched.set_index("index").sort_index()

        no_preceding = matched["_preceding_id"].isna()
        rejected = df.loc[matched.index[no_preceding]].assign(
            reason="future date, and no earlier transaction id to take a date from"
        )
        dated = matched[~no_preceding]

        out = df.drop(index=rejected.index)
        if dated.empty:
            return RuleResult(data=out, rejected=rejected)
        out.loc[dated.index, "date"] = dated["_preceding_date"]
        flagged = out.loc[dated.index].assign(
            original_date=df.loc[dated.index, "date"],
            reason="future date replaced with the date of preceding transaction "
            + dated["_preceding_id"],
        )
        return RuleResult(data=out, rejected=rejected, flagged=flagged, fixed_count=len(dated))
