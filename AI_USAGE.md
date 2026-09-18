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

### 3. Quality gates (my requirements)

- I asked for pre-commit hooks enforcing type annotations, Google-style
  docstrings on every function with parameter and return types, and every
  Pylance error.
- The AI pointed out that ruff's docstring rules skip private functions and never
  compare documented types with the signature, and wrote an AST checker
  (`tools/check_docstrings.py`) that does both. I had it tested against
  deliberately broken samples before accepting it.
- For Pylance, it ran Pyright (Pylance's engine) in the same `standard` mode as
  my editor rather than `strict`, whose 36 extra errors were pandas-stub noise.
- **AI error caught by the gates:** when the AI rewrote docstrings in bulk, it
  dropped the `...` body from two Protocol methods. mypy accepted this; Pyright
  flagged it, which justified adding it as a separate gate.

### 4. Validation layer

- Every rule from the design, built test-first, plus YAML config with CLI
  overrides, store/region/date filters, JSON-lines logs and a run manifest.
- Expected counts in the real-data tests come from a separate pandas script,
  not from the pipeline, so a test can disagree with the code.
- **AI error caught:** the design recorded the 143 repeated transaction ids as
  "byte-identical copies". Writing the independent expected counts showed only
  138 are; in 5 ids the rows differ in the sign of `quantity`. Treating those as
  plain conflicts would have discarded 5 real sales. The duplicate rule was split
  so conflicts are checked after row-level validation, which keeps the valid row.
  The Day-1 figure of 4,345 KRS rows was likewise a pre-deduplication count; the
  correct figure is 4,324.

### 5. KPIs, report and documentation

- KPIs built test-first against hand-worked examples; chain totals (revenue,
  cost, margin %, S-001 turnover) asserted against the independent pandas script.
- Before writing the turnover formula, the AI profiled the inventory file and
  found the weekly snapshots are independent samples (closing stock matches the
  next week's opening in 3 of 667 cases). That shaped the formula and is
  documented as an assumption rather than hidden.
- Charts follow a written data-visualisation method (single series, no dual
  axes, table beside every chart). The AI rendered the report in headless Edge
  and inspected screenshots rather than trusting the code.
- **AI errors caught:**
  - The first render had cramped article tables, right-aligned prose and bar
    value labels cut off by the neighbouring chart. All three were found from
    screenshots, not tests.
  - A README headline said "7,000+ values repaired"; checking it against the
    rule counts gave 8,027.
  - One small function (possible returns) had its implementation written in
    the same step as its test, so the test was never seen failing first. It
    is a slip in the test-first discipline, noted rather than hidden.

### 6. Independent structural review of the finished code

- Built a knowledge graph of the whole repository (`graphify`) to check the
  architecture from outside the code: 59 files → 567 nodes, 992 edges. Code
  structure comes from AST parsing; the documents are read by a separate pass
  that labels every edge `EXTRACTED`, `INFERRED` or `AMBIGUOUS`.
- **What it confirmed.** `RuleResult` and `Severity` are the two most connected
  types in the codebase, and both are touched by exactly the same 15 rule
  classes: every class that declares a severity also returns a `RuleResult`.
  `Rule` is a `Protocol`, so nothing forces that — the graph verifies the
  contract holds with no partial implementations, independently of mypy.
  `run_pipeline()` has 25 outward edges and 2 inward ones (the CLI and the
  tests), which is the shape a composition root should have.
- **AI errors caught:**
  - The document pass invented a relationship: it linked the 2027-dated
    transactions to the duplicate `transaction_id` finding as
    "semantically similar", reasoning that both look like deliberately seeded
    defects. No document says that — `docs/data-quality.md` attributes
    "suggests injected records" to the 2027 rows only. The edge was deleted, not
    downgraded, and the extraction prompt was tightened to forbid similarity
    edges justified by an inferred shared origin.
  - My own first correction was also wrong. I proposed keeping the edge under a
    weaker label, on the theory that the duplicate rules must run before
    `InferFutureDatesFromIdOrder` for the id sequence to be usable. Running that
    rule against three frames — deduplicated, exact copy present, sign-conflict
    pair present — gave identical results: the repair is invariant to duplicates,
    because the ordering check is non-strict. The hypothesis was dropped rather
    than shipped as a plausible-sounding edge.
  - The graph was missing a relationship the documents state outright: ADR 0005
    opens by naming the 2027 finding as the reason for the decision, but that
    finding was linked only to the data-quality table. Added as `EXTRACTED`.
- **Why the audit trail mattered.** The fabricated edge was findable only because
  the tool records its own confidence and reasoning per edge. Re-running the
  document pass with the tightened prompt produced zero `AMBIGUOUS` edges and
  recovered the missing ADR 0005 link on its own.

## Reflection

To be completed at submission, with an honest AI / human ratio.
