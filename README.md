# Retail Analytics Pipeline

Validates, cleans and reports on one month of sales and inventory data for a
five-store Turkish retail chain. The brief is in [case_study.md](case_study.md).

**The report produced from the provided data is in [report/](report/):** open
[report/report.html](report/report.html) in a browser (works offline). It filters
itself — pick stores, a region and a date range at the top and every figure, table
and chart re-aggregates without re-running the pipeline.

## What it does

1. **Loads** the four CSVs as text, exactly as written.
2. **Validates** the full input with 38 rules. Each issue is *fixed* when recovery
   is provable, *rejected* to a quarantine file when the row is unusable, or
   *flagged* for review while kept. Every row is accounted for:
   raw = clean + quarantined.
3. **Filters** clean data by store, region and date range — on the command line for
   the run, and again inside the report for the reader
   ([ADR 0008](docs/adr/0008-in-report-filtering.md)). Validation always runs on the
   full files first, so the data-quality figures never change with the selection.
4. **Computes KPIs:** revenue and gross margin by store, category, month, week
   and day; top/bottom 10 articles by revenue, margin (TRY) and margin %;
   inventory turnover by store; a sales-vs-inventory comparison; possible returns.
5. **Writes** an HTML report with charts, a CSV per table, a structured log and a
   run manifest.

## Headlines from the provided data

- **Revenue 57.4M TRY at a 17.9% gross margin** across 5 stores, March 2024.
  The two hypermarkets (Ankara, Antalya) bring 55% of revenue; store margins sit
  in a narrow 17.2–18.2% band.
- **Electronics is half of revenue (28.9M TRY) at 17.0% margin;** Grocery and
  Apparel earn the best margins (21.4%, 20.8%), Fresh Produce the worst (10.2%).
- **Some articles lose money:** four articles cost more than their recommended
  price, and a high-volume meat article (ART-00024) sold 1,091 units at a
  −29.6% margin.
- **Possible returns worth 1.18M TRY** (576 negative-quantity lines) are excluded
  from revenue, about 2% of it.
- **Inventory turnover is 0.82–0.99 for the month** on the sampled articles;
  Izmir turns stock fastest, the hypermarkets slowest.
- **Data quality:** 830 of 28,890 transactions quarantined (138 duplicates, 577
  negative quantities, 115 at unknown store S-099); 8,027 values repaired
  (KRS prices, day-first dates, missing-value spellings, 15 future dates).
  Details in [docs/data-quality.md](docs/data-quality.md).

## Setup

With [uv](https://docs.astral.sh/uv/) (installs Python 3.14 if needed):

```bash
uv sync
```

Without uv, on Python 3.14:

```bash
python -m venv .venv
.venv/Scripts/activate        # Windows; on macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

(Without uv, drop the `uv run` prefix from the commands below.)

## Run

```bash
uv run retail-analytics run                                  # everything
uv run retail-analytics run --store S-001 --store S-002      # some stores
uv run retail-analytics run --region Marmara                 # a region
uv run retail-analytics run --from 2024-03-01 --to 2024-03-15
uv run retail-analytics run --output-dir report              # regenerate report/
uv run retail-analytics run --help
```

Settings are read from [config/default.yaml](config/default.yaml) (or `--config
PATH`); command-line flags override them. The file also holds the price-outlier
tolerance, the ranking size and the minimum units for margin % rankings. An
unknown store or region, an invalid setting or a missing input file stops the run
with a message and exit code 1; a selection with no sales still produces a report
that says so.

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

## Project layout

```
src/retail_analytics/
  cli.py, config.py        command line, YAML + CLI settings
  pipeline.py              load -> validate -> filter -> KPIs -> write
  filters.py               store, region and date selection
  io/                      CSV reader, run manifest
  validation/              rule protocol, engine, rules, ordered registry
  kpis/                    sales, articles, inventory, returns
  reporting/               report model, writers, charts, HTML template
tests/                     rules, engine, KPIs, pipeline on real data, CLI
tools/check_docstrings.py  docstring gate used by pre-commit
```

**To extend:** a new data check is a class with `apply(df, tables)` added to
`validation/registry.py`; a new KPI is a function over the enriched sales added to
`pipeline._compute_kpis`; a new output format is a class with
`write(report, out_dir)` passed to `run_pipeline`.

## Testing

```bash
uv run pytest
```

- **Rules and KPIs** are tested on small hand-built tables with hand-worked
  expected values.
- **The pipeline** runs on the real `data/`; its expected counts and totals come
  from an independent pandas script, not from this code, so the tests can
  disagree with it.
- **The CLI** is tested for filters, config overrides and error exits.
- **The report's own filters** are driven in a headless browser (Playwright) and
  compared with the same independent script, so the figures the page computes for a
  selection cannot drift from the ones the pipeline would produce.

## Development

```bash
uv run pre-commit install    # once: lint, format, types, docstrings on every commit
uv run ruff check .          # lint
uv run mypy src tests tools  # type check (strict)
uv run pyright               # type check (Pylance engine)
```

## Documentation

- [docs/data-quality.md](docs/data-quality.md) — every check, what it found, how it is handled
- [docs/assumptions.md](docs/assumptions.md) — how ambiguities are resolved
- [docs/adr/](docs/adr/) — design decisions and their trade-offs
- [docs/design-session.md](docs/design-session.md) — the design interview, as it happened
- [AI_USAGE.md](AI_USAGE.md) — how AI tools were used
