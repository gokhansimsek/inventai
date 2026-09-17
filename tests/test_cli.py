from pathlib import Path

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
