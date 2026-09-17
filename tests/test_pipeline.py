from pathlib import Path

import pandas as pd

from retail_analytics.config import Settings
from retail_analytics.pipeline import run_pipeline

DATA_DIR = Path(__file__).parents[1] / "data"


def test_every_raw_row_is_either_processed_or_quarantined(tmp_path: Path) -> None:
    result = run_pipeline(Settings(data_dir=DATA_DIR, output_dir=tmp_path))

    for table, counts in result.row_counts.items():
        assert counts.raw == counts.clean + counts.rejected, table
        quarantine_file = tmp_path / "quarantine" / f"{table}.csv"
        if counts.rejected:
            assert len(pd.read_csv(quarantine_file)) == counts.rejected, table

    assert result.row_counts["transactions"].raw == 28_890
    assert (tmp_path / "report.html").is_file()
    assert (tmp_path / "kpis" / "revenue_by_store.csv").is_file()
