# 0006 — One report model, HTML and CSV writers

**Context.** Stakeholders need a readable report; other tools need the numbers.
Formatting mixed into KPI code would make both harder to change.

**Decision.** The pipeline builds a `Report` (KPI tables, data-quality results,
quarantined and flagged rows) with no presentation in it. Writers implement one
method, `write(report, out_dir) -> list[Path]`:

- `HtmlWriter`: one self-contained HTML file with Plotly charts, the Plotly library
  inlined so it opens offline, and a table beside every chart.
- `CsvWriter`: one CSV per KPI, quarantine and issues table.

Each run also writes `run_manifest.json` (settings, input hashes, row counts) and
`run.log.jsonl` (structured log).

**Consequences.** Adding Excel or PDF output is one new writer. KPI functions return
plain DataFrames and are tested without any rendering. The HTML file is about 5 MB
because it embeds Plotly; that is the price of opening it with no network access.
