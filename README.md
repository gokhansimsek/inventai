# Retail Analytics Pipeline

Validates, cleans and reports on one month of sales and inventory data for a
five-store Turkish retail chain. The brief is in [case_study.md](case_study.md).

> **Status:** work in progress. Validation is complete (see
> [docs/data-quality.md](docs/data-quality.md)); revenue by store is the only KPI
> so far.

## Setup

Requires [uv](https://docs.astral.sh/uv/) (it installs Python 3.14 if needed):

```bash
uv sync
```

## Run

```bash
uv run retail-analytics run                                  # everything
uv run retail-analytics run --store S-001 --store S-002      # some stores
uv run retail-analytics run --region Marmara                 # a region
uv run retail-analytics run --from 2024-03-01 --to 2024-03-15
uv run retail-analytics run --output-dir report              # fixed folder
uv run retail-analytics run --help
```

Settings are read from [config/default.yaml](config/default.yaml) (or `--config
PATH`); command-line flags override them. An unknown store or region, an invalid
setting or a missing input file stops the run with a message and exit code 1.

Each run writes to `output/<timestamp>/` unless `--output-dir` is given:

| Path | Contents |
|---|---|
| `report.html` | The report; open in a browser |
| `kpis/*.csv` | One file per KPI table |
| `quarantine/<table>.csv` | Rows that could not be used, with `reason` and `rule_id` |
| `issues/<table>.csv` | Rows kept but flagged for review, with `reason` and `rule_id` |
| `data_quality.csv` | Every rule, and how many rows it fixed, rejected and flagged |
| `row_counts.csv` | Raw = clean + rejected, per input file |
| `run.log.jsonl` | The run's log, one JSON event per line |
| `run_manifest.json` | Settings used, input file hashes and row counts |

## Development

```bash
uv run pre-commit install    # once: lint, format, types, docstrings on every commit
uv run pytest                # tests
uv run ruff check .          # lint
uv run mypy src tests tools  # type check (strict)
uv run pyright               # type check (Pylance engine)
```

## Documentation

- [docs/data-quality.md](docs/data-quality.md) — every check, what it found, how it is handled
- [docs/design-session.md](docs/design-session.md) — the design decisions, as they were made
- [AI_USAGE.md](AI_USAGE.md) — how AI tools were used
