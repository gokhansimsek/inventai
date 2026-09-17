# Grilling Session — Retail Analytics Case Study

> Resume file. Written before a session restart so the `/grill-me` skill
> (`mattpocock-skills` plugin) can pick the tree back up.
> Target: `case_study.md`. Repo state at time of writing: empty apart from
> `case_study.md` and `data/`. No implementation exists yet.

## Method

The `grilling` skill maps the work as a **design tree**. Each round asks the
**frontier** — every decision whose prerequisites are already settled — in one
batch, with a recommended answer per question. The user's answers push the
frontier outward and unblock the next round. Session ends when the frontier is
empty. Fact-finding is the agent's job; decisions are the user's.

---

## Facts established (agent-found, not user-supplied)

Probed directly from `data/` before Round 1, so no question below asks the user
for something lookup-able.

| Finding | Detail |
|---|---|
| `KRS` currency | 4,345 rows (15%). Median 49,582 vs TRY's 501 — **exactly 100x**. It is kurus. |
| Mixed date formats | 27,482 ISO + 1,408 `DD-MM-YYYY`. 838 of those have first part >12, and none have second part >12 — **unambiguously DD-MM**. |
| Future dates | 15 rows dated Jan–Feb **2027**, against a Mar-2024 dataset. |
| Duplicate `transaction_id` | 143 ids, and the rows are **byte-identical copies**. |
| Non-positive `quantity` | 577 rows with qty <= 0. |
| Missing `customer_id` | 569 rows (brief says walk-ins — likely legitimate, not a defect). |
| Referential integrity | Zero orphan `article_id`s in transactions. |
| Discount range | 0.0 to 40.0 pct. |
| Row counts | transactions 28,890 · inventory 1,326 · articles 200 · stores 5. |

Reproduce commands: see git history / rerun with `awk` over `data/*.csv`.

---

## Answers log

- **Q1 → (a) + (b) weighted equally.** User has **3 days** (not 4–6h); goal is
  the best submission possible. Guard: architecture must stay proportionate so
  "Pragmatism" doesn't suffer.
- **Q2 → pandas + pandera.**
- **Q3 → per-file quarantine.** Each CSV gets its own quarantine table/file for
  rows that can't be fixed by an exact rule; kept for later human review. Only
  provably-fixable issues are repaired. All correct data is processed.
- **Q4 → HTML report + CSVs, both behind one small writer interface.**
- **Q5 → (c)** YAML (typed pydantic settings) + CLI overrides.
- **Q6 (AI log / commits) → still open.**

## Facts found in second probe (2026-09-17)

| Finding | Detail |
|---|---|
| Orphan store `S-099` | 116 transactions reference a store not in `stores.csv` (resume file's "zero orphans" only checked articles). |
| `S-004` opening_date `2027-03-15` | Future date, yet it has 7,534 transactions (26%) in Mar 2024. |
| Region values | Real values are Turkish regions (Marmara, Aegean, Central Anatolia, Mediterranean) — brief's "North/South/..." is wrong. |
| Missing customer_id tokens | `''` 569 · `N/A` 594 · `NULL` 573 · `NA` 563 = **2,299** (earlier 569 counted only blanks). |
| Negative quantity | 577 rows, all -1..-5; no zero qty. Max qty 5 — no qty outliers. |
| Selling price vs RSP | Price (after KRS fix) always 0.95–1.05x RSP — no price outliers. |
| Articles cost > RSP | 4 articles. 2,810 transactions sell below cost after discount. |
| Inventory balance | 28 rows where opening + received - sold != closing (off by ±1..10). No nulls, negatives, dup keys or orphans. |
| Inventory snapshots | Mondays 03-04, 03-11, 03-18, 03-25. Sales run 03-01..03-31; 3,006 sales before first snapshot. |
| Inventory vs sales | Inventory covers 497 store-article pairs; sales cover 1,038. Weekly `sold_qty` does **not** reconcile with transactions (ratio median 1.26, range 0–50). The files are independent. |
| Clean date range | 28,875 rows in 2024-03-01..31; 15 rows in 2027. |

## Round 2 answers

- **Q6 → (c)** running `AI_USAGE.md`, small commits, keep this session file in repo as design record.
- **Q7 → (b)** two severities: *reject* (→ per-file quarantine, cascades to children) vs *flag* (row kept, logged to per-file issues table). S-004 opening date, inventory imbalance, below-cost articles = flag.
- **Q8 → (c)** reject negative qty; report "possible returns" count + value.
- **Q9 → (a) but user does NOT want the 15 rows lost** — find a logical way to process them. Follow-up in Round 3 (Q15).
- **Q10 → accepted**: revenue = qty × TRY price × (1−disc); cost = qty × current purchase_price; margin % plus margin TRY; below-cost sales kept and surfaced as insight.
- **Q11 → (c)** turnover from inventory file only (sold_qty × cost / avg of weekly (open+close)/2 at cost), period-not-annualised, plus a sales-vs-inventory reconciliation table.
- **Q12 → accepted** layout + uv/ruff/mypy/pytest; **also create a project-local Python venv**.
- **Q13 → (b)** table-driven rule tests, hand-computed KPI tests, end-to-end raw = clean + quarantined reconciliation.
- **Q14 → (b) structured JSON logs** (user wants them consumable elsewhere); per-run `output/<timestamp>/` with manifest still assumed.

## Facts found in third probe

| Finding | Detail |
|---|---|
| 2027 rows | IDs `TXN-128733..128747` — contiguous, immediately after the last valid id `128732`. Only 3 dates (2027-01-15, 01-22, 02-01). All `Sunny`, all discount 0 (vs 17% / 70% base rates) — looks injected. |
| ID ↔ date | Across all 28,875 valid rows, `transaction_id` order is **strictly monotonic with date** (100001 = 03-01 … 128732 = 03-31). |
| Article coverage | All 200 articles have sales (min 21 lines) — bottom-10 never hits zero-sale articles. |
| Env | `uv 0.9.12` installed; Pythons 3.14.5 (default), 3.13.9, 3.12. |

## Round 3 answers

- **Q15 → (a)** infer date 2024-03-31 from monotonic transaction_id; keep row, `date_inferred=true`, log to transactions issues table with original value.
- **Q16 → (b)** turnover uses only inventory weeks fully inside the date range; print effective period; "n/a" if no full week.
- **Q17 → (c)** six lists: top/bottom 10 by revenue, margin %, margin TRY; min-units threshold (YAML) for margin % lists; rankings respect filters.
- **Q18 → (b)** monthly + daily + weekly trend.
- **Q19 → (b)** Jinja2 + Plotly, JS inlined, offline, self-contained.
- **Q20 → (b)** typer; filter values validated against master data with friendly errors.
- **Q21 → (a)** stdlib logging + custom JSON formatter → `run.log.jsonl`; human-readable console.
- **Q22 → uv + `.venv` + `uv.lock` + exported `requirements.txt`, Python 3.14.** Verified: 3.14.5 installs pandas 3.0.5, pandera 0.33.1 (lazy validation works), pydantic 2.13.5, plotly 7.1.0, typer, jinja2, pytest, mypy, ruff.
- **Q23 → (b)** README + `docs/data-quality.md`, `docs/assumptions.md`, `docs/adr/`, `AI_USAGE.md`, `docs/design-session.md`.

## Round 4 answers

- **Q24 → (b)** `output/` git-ignored (timestamped runs); `make report` writes full-data run to committed `report/`.
- **Q25 → (c)** fail-fast (non-zero exit, clear message) on missing file / missing column / unparseable column / invalid config; empty filter result → report saying "no data for this selection", exit 0.
- **Q26 → (b)** thin end-to-end slice on day 1, then widen; rules and KPIs built test-first (TDD skill); docs + AI_USAGE updated per milestone.

**Frontier empty — awaiting user confirmation of the design summary before implementation.**

## Round 1 — root frontier (answered, see Answers log)

### Q1 — What is this submission optimizing for?

4–6 hours against six evaluation criteria. You cannot max all six. Three postures:

- **(a) Data-quality showcase** — rigorous, well-tested validation layer, quality report as a first-class output, KPIs computed straightforwardly on top.
- **(b) Architecture showcase** — clean layered pipeline, protocols/interfaces, DI, pluggable readers and writers; scales to 50 KPIs.
- **(c) Analytical showcase** — depth on business questions, extra KPIs, weather/discount elasticity, sharp narrative.

**Recommendation: (a), with just enough of (b) to look production-shaped.**
The closing note of the brief ("The data quality issues are intentional and part
of the evaluation") is the loudest signal in the document, and "Data Quality
Handling" is criterion #1. (b) is where most candidates over-invest and produce
six layers of abstraction over 200 lines of pandas — actively bad signal against
the "Pragmatism" criterion. Take (c) as a paragraph of commentary in the report,
not as code.

### Q2 — Compute stack

- **(a) pandas** — universal, instantly readable by any reviewer.
- **(b) polars** — faster, better types, signals currency; smaller reviewer pool.
- **(c) DuckDB + SQL** — KPI layer becomes readable SQL over the CSVs, validation stays in Python.

**Recommendation: (a) pandas.** Dataset is 2 MB; performance is irrelevant, so
polars buys nothing but a chance the reviewer isn't fluent. Reviewer legibility
is the actual currency. Add `pandera` (or typed dataclass schemas) for the
validation layer — that's where a library choice genuinely earns its keep.

### Q3 — Validation philosophy (the big branch)

Given a row with `quantity = -3`, does the pipeline:

- **(a) fail-fast** — abort the run, make a human fix the input;
- **(b) quarantine** — drop the row to a `rejected/` artifact with a reason code, continue on survivors, report rows lost;
- **(c) repair-in-place** — apply a documented coercion and log every mutation.

**Recommendation: (b) as default, (c) for a small explicit whitelist.**
Provably recoverable rules get repaired — KRS→TRY is a proven 100x and the DD-MM
dates are proven unambiguous, so refusing to fix those is pedantry. Everything
judgemental (negative qty, 2027 dates) is quarantined with a reason code, never
silently dropped. Fail-fast is wrong for a batch analytics job — one bad row
shouldn't deny the ops team their month. Key property this buys: **every rejected
row is counted, attributed to a rule, and surfaced in the report**, so revenue is
always reconcilable against raw input.

### Q4 — Report format

- **(a) Excel, multi-sheet** — one sheet per KPI plus a data-quality sheet.
- **(b) Self-contained HTML** — narrative, tables and charts in one file.
- **(c) CSVs per KPI** — diffable, machine-readable, zero presentation.

**Recommendation: (b) HTML, with (c) written alongside as the machine-readable
artifact.** The brief asks for a report "a business stakeholder could review" —
a prose-and-charts ask. HTML costs far less time than Excel formatting and looks
dramatically better. Emitting raw CSVs too is nearly free and shows you
distinguish a presentation layer from a data layer. Skip PDF; toolchain pain
isn't worth it.

### Q5 — Configuration surface

Brief wants store/region filtering and a date range.

- **(a) CLI only** (`argparse`/`typer`).
- **(b) YAML config file** passed by path.
- **(c) Both** — YAML for defaults and paths, CLI flags override per-run.

**Recommendation: (c), kept thin.** YAML for stable things (data dir, output dir,
outlier z-score threshold, currency rates); CLI flags for per-run selection
(`--store`, `--region`, `--from`, `--to`). The reason isn't elegance — it's that
**validation thresholds belong in config, not code**, and once you accept that
you need the file anyway. Avoid the over-engineering trap: no config
inheritance, no profiles, no env-var layer.

---

## Round 2 — blocked, do not ask yet

Each of these has an unsettled prerequisite in Round 1.

| Question | Blocked on |
|---|---|
| Inventory turnover formula — only 4 weekly snapshots and 1 month of sales; what is "average inventory", and does COGS come from `sold_qty` or from transactions? | Q1, Q3 |
| Gross margin denominator — revenue after discount vs gross revenue; and what happens when `purchase_price > selling_price`. | Q3 |
| Whether the 2027-dated rows are quarantined or clamped, and whether the configurable date range silently hides them. | Q3, Q5 |
| Test strategy and depth — which computations get unit tests, whether validation rules get table-driven tests. | Q1, Q2 |
| AI Usage Log strategy — the brief explicitly requires declaring AI use, including the AI/human ratio. Depends on how much of the build is delegated. | Q1 |
| Module boundaries and package layout. | Q1, Q2, Q3 |
| Logging approach — stdlib `logging` config, structured vs plain, and what the quality layer emits. | Q2, Q3 |

---

## How to resume

After restart, run `/grill-me` and point it at this file. Answer Round 1, then
the frontier recomputes and Round 2 opens.
