from collections.abc import Mapping

import pandas as pd

from retail_analytics.validation.base import Rule, RuleResult, Severity
from retail_analytics.validation.engine import RowCounts, validate
from retail_analytics.validation.generic_rules import RejectUnknownReference


class RejectStoreTwo:
    rule_id = "TEST_REJECT_S2"
    table = "stores"
    severity = Severity.REJECT
    description = "Test double: rejects store S-2."

    def apply(self, df: pd.DataFrame, tables: Mapping[str, pd.DataFrame]) -> RuleResult:
        bad = df["store_id"] == "S-2"
        return RuleResult(data=df[~bad], rejected=df[bad].assign(reason="test"))


def test_rows_referencing_a_rejected_parent_are_quarantined_too() -> None:
    raw = {
        "stores": pd.DataFrame({"store_id": ["S-1", "S-2"]}),
        "transactions": pd.DataFrame(
            {"transaction_id": ["T1", "T2", "T3"], "store_id": ["S-1", "S-2", "S-9"]}
        ),
    }
    rules: list[Rule] = [
        RejectStoreTwo(),
        RejectUnknownReference("transactions", "store_id", "stores"),
    ]

    outcome = validate(raw, rules)

    assert outcome.clean["transactions"]["transaction_id"].tolist() == ["T1"]
    assert outcome.rejected["transactions"][["transaction_id", "reason", "rule_id"]].to_dict(
        "records"
    ) == [
        {
            "transaction_id": "T2",
            "reason": "store_id 'S-2' not found in stores",
            "rule_id": "TRANSACTIONS_STORE_ID_UNKNOWN",
        },
        {
            "transaction_id": "T3",
            "reason": "store_id 'S-9' not found in stores",
            "rule_id": "TRANSACTIONS_STORE_ID_UNKNOWN",
        },
    ]
    assert outcome.row_counts == {
        "stores": RowCounts(raw=2, clean=1, rejected=1),
        "transactions": RowCounts(raw=3, clean=1, rejected=2),
    }
    assert [(o.rule_id, o.fixed, o.rejected, o.flagged) for o in outcome.rule_outcomes] == [
        ("TEST_REJECT_S2", 0, 1, 0),
        ("TRANSACTIONS_STORE_ID_UNKNOWN", 0, 2, 0),
    ]
