# Retail Analytics Pipeline

Validates, cleans and reports on one month of sales and inventory data for a
five-store Turkish retail chain. The brief is in [case_study.md](case_study.md).

> **Status:** work in progress. The first end-to-end version runs: it loads
> the data, applies the first validation rules, computes revenue by store and
> writes an HTML + CSV report.

## Setup

Requires [uv](https://docs.astral.sh/uv/) (it installs Python 3.14 if needed):

```bash
uv sync
```

## Run

```bash
uv run retail-analytics run                          # all stores -> output/
uv run retail-analytics run --store S-001 --store S-002
uv run retail-analytics run --help
```

Open `output/report.html` in a browser. Alongside it:

| Path | Contents |
|---|---|
| `kpis/*.csv` | One file per KPI table |
| `quarantine/<table>.csv` | Rows that could not be used, with `reason` and `rule_id` |
| `issues/<table>.csv` | Rows kept but flagged for review |
| `data_quality.csv` | Every rule and how many rows it affected |
| `row_counts.csv` | Raw = clean + rejected, per input file |

## Development

```bash
uv run pre-commit install    # once: lint, format, types, docstrings on every commit
uv run pytest                # tests
uv run ruff check .          # lint
uv run mypy src tests tools  # type check (strict)
uv run pyright               # type check (Pylance engine)
```

## Documentation

- [docs/design-session.md](docs/design-session.md) — the design decisions, as they were made
- [AI_USAGE.md](AI_USAGE.md) — how AI tools were used
