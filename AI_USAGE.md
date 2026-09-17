# AI Usage Log

Kept up to date at each milestone rather than written at the end.

## Tools

- **Claude Code (Claude Opus 5)**, in VS Code, for data profiling, design
  review, and writing code and tests.

## Milestone log

### 1. Design (before any code)

- Claude profiled the CSVs and proposed decisions in rounds, each with a
  recommendation. I answered every question; the full record is in
  [docs/design-session.md](docs/design-session.md).
- **Where I overrode or extended the AI:**
  - Weighted architecture equally with data quality (AI recommended data quality first).
  - Refused to discard the 15 rows dated 2027 when the AI recommended
    quarantining them. That pushed a second look at the data, which found
    transaction IDs are strictly ordered by date, and the rows could be dated
    from that evidence.
  - Chose structured JSON logs over plain text so logs can be consumed elsewhere.
  - Chose Python 3.14 over the AI's suggested 3.12; the AI verified the stack
    installs and works on 3.14 before accepting it.
- **AI errors caught:** the first data profile undercounted missing customer ids
  (569 vs 2,299 — it only counted blanks, not `N/A`/`NULL`/`NA`) and missed the
  unknown store `S-099`. A second, pandas-based profile corrected both.

### 2. First end-to-end version

- Built test-first (red → green per behaviour) at seams I agreed in advance:
  rules, validation engine, KPI functions, pipeline, CLI.
- Every figure the tests assert (e.g. 4,345 KRS rows, 577 negative quantities)
  was checked against the independent data profile, not taken from the code.
- **Adjustment:** `make report` was planned, but `make` isn't available on
  Windows; the report is generated through the CLI instead.

## Reflection

To be completed at submission, with an honest AI / human ratio.
