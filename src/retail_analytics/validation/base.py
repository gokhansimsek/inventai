"""Building blocks shared by every validation rule.

A rule looks at one table and returns what survives, what was quarantined,
and what was flagged for review. Rules never drop rows silently: anything
removed from ``data`` must appear in ``rejected``.
"""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol

import pandas as pd


class Severity(StrEnum):
    FIX = "fix"  # provably recoverable; value corrected in place
    REJECT = "reject"  # unusable for any KPI; row moved to quarantine
    FLAG = "flag"  # suspicious but usable; row kept and recorded for review


def _empty() -> pd.DataFrame:
    """Create the default value for result tables a rule did not produce.

    Returns:
        pd.DataFrame: An empty DataFrame.
    """
    return pd.DataFrame()


@dataclass(frozen=True)
class RuleResult:
    data: pd.DataFrame
    rejected: pd.DataFrame = field(default_factory=_empty)
    flagged: pd.DataFrame = field(default_factory=_empty)
    fixed_count: int = 0


class Rule(Protocol):
    rule_id: str
    table: str
    severity: Severity
    description: str

    def apply(self, df: pd.DataFrame) -> RuleResult:
        """Check a table and split its rows by outcome.

        Args:
            df (pd.DataFrame): The table as left by the previous rule.

        Returns:
            RuleResult: Rows that continue (possibly corrected), rows quarantined, rows
                flagged for review, and how many values were fixed.
        """
        ...
