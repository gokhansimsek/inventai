"""Everything a report shows, independent of how it is written."""

from dataclasses import dataclass
from datetime import datetime

import pandas as pd


@dataclass(frozen=True)
class Report:
    generated_at: datetime
    kpis: dict[str, pd.DataFrame]
    data_quality: pd.DataFrame
    row_counts: pd.DataFrame
    quarantine: dict[str, pd.DataFrame]
    issues: dict[str, pd.DataFrame]
