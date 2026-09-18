"""Everything a report shows, independent of how it is written."""

from dataclasses import dataclass
from datetime import datetime

import pandas as pd


@dataclass(frozen=True)
class Report:
    generated_at: datetime
    selection: str
    has_sales: bool
    kpis: dict[str, pd.DataFrame]
    turnover_weeks: list[pd.Timestamp]
    top_n: int
    min_units_for_margin_pct: int
    data_quality: pd.DataFrame
    row_counts: pd.DataFrame
    quarantine: dict[str, pd.DataFrame]
    issues: dict[str, pd.DataFrame]
    facts: dict[str, pd.DataFrame]
