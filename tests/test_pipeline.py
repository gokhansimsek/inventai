import json
from datetime import date
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


def test_known_data_issues_are_found_in_the_real_data(tmp_path: Path) -> None:
    # Expected counts come from an independent pandas profile of data/, not from this code.
    result = run_pipeline(Settings(data_dir=DATA_DIR, output_dir=tmp_path))

    found = {o.rule_id: (o.fixed, o.rejected, o.flagged) for o in result.rule_outcomes}
    assert found["TRANSACTIONS_EXACT_COPY"] == (0, 138, 0)
    assert found["TRANSACTIONS_CUSTOMER_ID_MISSING_SPELLINGS"] == (2292, 0, 0)
    assert found["TRANSACTIONS_DATE_FORMAT"] == (1396, 0, 0)
    assert found["TRANSACTIONS_DATE_IN_FUTURE"] == (15, 0, 15)
    assert found["TRANSACTIONS_KRS_TO_TRY"] == (4324, 0, 0)
    assert found["TRANSACTIONS_QUANTITY_NOT_POSITIVE"] == (0, 577, 0)
    assert found["TRANSACTIONS_KEY_CONFLICT"] == (0, 0, 0)
    assert found["TRANSACTIONS_STORE_ID_UNKNOWN"] == (0, 115, 0)
    assert found["STORES_OPENING_DATE_IN_FUTURE"] == (0, 0, 1)
    assert found["ARTICLES_COST_ABOVE_RECOMMENDED_PRICE"] == (0, 0, 4)
    assert found["INVENTORY_STOCK_IMBALANCE"] == (0, 0, 28)


def _revenue(output_dir: Path) -> pd.DataFrame:
    return pd.read_csv(output_dir / "kpis" / "revenue_by_store.csv")


def test_region_filter_keeps_only_that_regions_stores(tmp_path: Path) -> None:
    run_pipeline(Settings(data_dir=DATA_DIR, output_dir=tmp_path, regions=("Marmara",)))

    revenue = _revenue(tmp_path)
    assert revenue["store_id"].tolist() == ["S-001", "S-005"]
    assert round(revenue["revenue"].sum(), 2) == 17_198_488.99


def test_date_range_keeps_only_sales_inside_it(tmp_path: Path) -> None:
    day = date(2024, 3, 10)
    run_pipeline(Settings(data_dir=DATA_DIR, output_dir=tmp_path, date_from=day, date_to=day))

    assert round(_revenue(tmp_path)["revenue"].sum(), 2) == 2_395_207.43


def test_run_manifest_records_settings_row_counts_and_input_hashes(tmp_path: Path) -> None:
    run_pipeline(Settings(data_dir=DATA_DIR, output_dir=tmp_path, stores=("S-001",)))

    manifest = json.loads((tmp_path / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["settings"]["stores"] == ["S-001"]
    assert manifest["row_counts"]["transactions"]["raw"] == 28_890
    assert set(manifest["input_files"]) == {
        "stores.csv",
        "articles.csv",
        "transactions.csv",
        "inventory.csv",
    }
    assert all(len(f["sha256"]) == 64 for f in manifest["input_files"].values())
