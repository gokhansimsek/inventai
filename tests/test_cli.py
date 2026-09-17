import json
from pathlib import Path

import pandas as pd
from typer.testing import CliRunner

from retail_analytics.cli import app

DATA_DIR = Path(__file__).parents[1] / "data"
runner = CliRunner()


def test_unknown_store_stops_the_run_and_lists_valid_stores(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["run", "--data-dir", str(DATA_DIR), "--output-dir", str(tmp_path), "--store", "S-999"],
    )

    assert result.exit_code == 1
    assert "Unknown store 'S-999'" in result.output
    assert "S-001" in result.output
    assert "Traceback" not in result.output
    assert not (tmp_path / "report.html").exists()


def _run(*args: str) -> tuple[int, str]:
    result = runner.invoke(app, ["run", "--data-dir", str(DATA_DIR), *args])
    return result.exit_code, result.output


def test_unknown_region_stops_the_run_and_lists_valid_regions(tmp_path: Path) -> None:
    exit_code, output = _run("--output-dir", str(tmp_path), "--region", "North")

    assert exit_code == 1
    assert "Unknown region 'North'" in output
    assert "Marmara" in output
    assert "Traceback" not in output


def test_cli_flags_override_the_config_file_and_logs_are_json_lines(tmp_path: Path) -> None:
    config = tmp_path / "config.yaml"
    config.write_text("stores: [S-002]\nprice_tolerance: 0.4\n", encoding="utf-8")
    out = tmp_path / "run"

    exit_code, output = _run("--config", str(config), "--output-dir", str(out), "--store", "S-003")

    assert exit_code == 0, output
    assert pd.read_csv(out / "kpis" / "revenue_by_store.csv")["store_id"].tolist() == ["S-003"]
    manifest = json.loads((out / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["settings"]["price_tolerance"] == 0.4
    events = [json.loads(line) for line in (out / "run.log.jsonl").read_text().splitlines()]
    assert {"timestamp", "level", "logger", "message"} <= events[0].keys()
    assert any(e.get("rule_id") == "TRANSACTIONS_EXACT_COPY" for e in events)


def test_invalid_config_file_stops_the_run_with_a_clear_message(tmp_path: Path) -> None:
    config = tmp_path / "config.yaml"
    config.write_text("price_tolerence: 0.4\n", encoding="utf-8")

    exit_code, output = _run("--config", str(config), "--output-dir", str(tmp_path / "run"))

    assert exit_code == 1
    assert "price_tolerence" in output
    assert "Traceback" not in output
