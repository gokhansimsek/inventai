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

### 7. Report hierarchy and tabs

- I asked for a less flat report: the good KPIs and the problem data emphasised, and
  the sections tabbed. Recorded as [ADR 0007](docs/adr/0007-report-hierarchy-and-tabs.md).
- Reviewed in a real browser with Playwright rather than by reading the markup, which
  is how the checks below were confirmed: five tabs reachable by arrow key, every panel
  visible under print media, no horizontal scroll at a 390px viewport, no console
  errors. Page height for the first screen fell from 8,022px to 2,542px.
- **AI errors caught:**
  - The first pass gave the "possible returns" status dot no size rule, so it rendered
    as nothing. Found in the screenshot, not the code.
  - Plotly sizes a chart to its container, so the charts inside tabs that start hidden
    drew at zero width. They are resized when their tab is first opened, and on
    `beforeprint`.
  - The previous stat tiles set `font-variant-numeric: tabular-nums` on the large
    values, which makes display-size numbers look loose; that belongs on table columns
    only, and was removed from the headline figures.
- **Left alone deliberately:** the gross-margin-% bars are five near-identical lengths
  (17.2–18.2% on a 0–20% axis), so the chart carries no information the table doesn't.
  The honest fix is a dot plot, which the zero-baseline bar rule in the chart method
  does not cover; raised rather than changed, because the chart method is a settled
  decision.

### 8. Filtering inside the report

- I asked for store, region and date-range selection in the report itself, rather than
  only as CLI flags. That changes Q5 and [ADR 0006](docs/adr/0006-report-model-and-writers.md),
  so the AI raised the conflict and measured the options before writing anything:
  the fact cube is 10,789 rows and 0.3 MB, against a 4.7 MB file. Recorded as
  [ADR 0008](docs/adr/0008-in-report-filtering.md).
- **The risk I made it design around:** a second implementation of the analysis in
  JavaScript could disagree with the tested Python. The answer was to keep every formula
  in Python and give the page only pre-computed measures to sum, average and divide.
  Revenue and cost are additive, margin % is a ratio of sums, and turnover is summed
  COGS over mean weekly inventory value once the whole-week rule picks the weeks.
- **How it is held:** `tests/test_report_filters.py` drives the real controls in a real
  browser and compares the figures on screen with a standalone pandas script over
  `data/` — not with the pipeline, so the test can disagree with both. Three independent
  routes agree on all four selections. A test also asserts the data-quality totals do
  **not** move with the selection, because validation runs before filtering.
- I then asked for stores and regions as multi-select dropdowns rather than list boxes,
  and for the Articles tab to show one ranking measure at a time, defaulting to revenue.
- **AI errors caught:**
  - Possible returns are computed from quarantined rows, which are not in the sales
    cube, so that tile would have stayed frozen while everything else filtered. Caught
    by reading the masthead against the fact tables, and fixed with a returns cube.
  - Filtering to one store left the turnover chart 240px tall for a 104px bar: Plotly
    updates its own layout height but not the inline height on the container it created.
    Found by measuring the element in the browser, not from the screenshot.
  - Rounding the cube's measures to 2 decimals rounded before summing, so the page
    showed gross margin as 10,301,981 against the pipeline's 10,301,980. Spotted in a
    screenshot, confirmed by summing at 2dp, 4dp and full precision, and fixed by not
    rounding. The browser test had not covered gross margin in TRY; it does now, with
    values from the independent script.
  - Writing that test, the AI filled in three of the four expected margins from memory
    rather than from the independent script. Two were wrong. They now come from the
    script, like every other expected value in the suite.

### 9. Reviewing the filtering work

- I asked for a two-axis review of the three filtering commits against `origin/main`:
  one pass on the repo's documented standards, one on [ADR 0008](docs/adr/0008-in-report-filtering.md)
  as the spec, run as separate agents so neither could excuse the other. They returned
  11 and 9 findings. I then asked for them to be fixed.
- **What the review caught that mattered:**
  - The browser seam was agreed in ADR 0008 but never written into `CLAUDE.md`, so the
    two documents contradicted each other about which seams exist. `CLAUDE.md` now
    records it, including that the seam covers filter-driven page state.
  - ADR 0008 claimed the page "only sums, averages and divides" and never restates a
    formula. It also subtracted, and it recomputed which Monday starts a week from the
    date — a *rule*, and the one thing in the page that could genuinely have drifted
    from `enrich_sales`. The payload now carries a day → week lookup, and the ADR says
    what the page actually does.
  - The date controls took their maximum from the last clean sale. An inventory week
    counts towards turnover only if it ends inside the range, so on a run ending after
    the last sale, the page's own Reset would have dropped a week the server-rendered
    report used. Latent on this data, where both fall on 2024-03-31; fixed in
    `cube.date_bounds`, which spans the facts rather than the sales.
  - An undefined ratio printed as `inf`/`nan` in Python and `0.00` in the page. Both
    now print an em dash.
- **The AI error the fixes surfaced.** ADR 0008 said the expected values came from "a
  standalone pandas script over `data/`" — but that script was never committed, so
  nothing could be checked or rerun. Writing it as `tools/profile_selections.py`
  reproduced all six masthead figures for all four selections exactly, and the row
  counts in [docs/data-quality.md](docs/data-quality.md).
- **An AI error I caught in the review of the review.** The script first disagreed on
  one figure — possible returns for the whole month, by 961 TRY — and the AI reported
  that as a latent defect: one transaction is both non-positive in quantity and for the
  unknown store `S-099`, so the quarantine counts it under the quantity rule while the
  returns tile, scoped to known stores, does not. I asked for it to be fixed. It then
  found that [assumptions.md](docs/assumptions.md#sales) already settles exactly this
  ("excluded ... including from possible returns, so every figure covers the same
  stores"), as does `filters.filter_by_store`. It had read `docs/data-quality.md` and the code,
  but not the assumptions, so it presented a recorded decision as an accident — and
  nearly reversed it on my say-so. Nothing changed but the wording in
  `docs/data-quality.md`, which had stated the rule without its exception.
- **Left alone deliberately:** the review flagged `_compute_kpis`'s six parameters as a
  data clump, and that the ~600 lines of page JavaScript pass through none of the four
  gates. The first is churn in a signature that reads fine; the second would mean
  adding a JavaScript toolchain to a Python case study. Both raised, neither done.

### 10. Scalability review of the report

- I asked what happens to this design if the chain grows to Turkey-wide scale: 7 regions,
  1,000 stores. The AI generated scaled copies of `data/` keeping the same defect mix and
  rows-per-store, ran the real pipeline at 5, 50, 200 and 1,000 stores, timed every stage
  and every rule, and measured a real filter change in a real browser.
- **What it found.** The pipeline scales: nothing is quadratic, all 38 rules are
  vectorised, and 5.8M transactions validate in ~90 s. The limit there is memory, not
  time — reading every column as `dtype=str` costs ~740 bytes of RAM per 84-byte CSV row,
  so a full year at 1,000 stores would not fit in 32 GB. The report is what breaks first:
  127 MB, and 5.1 s per filter change.
- **What I had it fix.** The page built a `Date` per fact row to find its week and month.
  Reading both from the day lookup instead took a filter change from 5.1 s to 1.8 s, and
  it is the same change ADR 0008's no-drift argument already wanted, so it was worth doing
  at any size.
- **The AI error I caught.** Its first measurement of the fix reported no improvement at
  all. Its benchmark harness had its own copy of the aggregation loop rather than the
  page's, so it had been measuring the old code either way. Measuring the real report in
  a real browser gave the 5.1 s → 1.8 s above. A benchmark that does not run the code you
  changed will happily tell you your change did nothing.
- **Left alone deliberately.** Capping the per-store charts at a top-N would buy another
  ~1.1 s, but it changes what the report shows, so it is raised rather than done. The
  bigger items — dropping the article dimension from the page, chunked validation,
  cheaper dtypes — are recorded in ADR 0008 and left unbuilt: `design-session.md` settles
  that at 2 MB performance is irrelevant, and building for 1,000 stores in a case study
  is exactly the over-investment that document warns against.

## Reflection

To be completed at submission, with an honest AI / human ratio.
