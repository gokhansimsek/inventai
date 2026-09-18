# 0008 — The report filters itself, from pre-aggregated facts

**Context.** Requirement 4 asks for store, region and date-range configurability, and
Q5 of the design session answered it with YAML plus CLI flags. That is still how a run
is scoped, but it makes a stakeholder ask an engineer to re-run the pipeline before
they can see one store or one week. The report is the artifact they actually hold, and
it could answer those questions itself.

The risk in doing so is a second implementation of the analysis. If the page computed
revenue, margin or turnover in JavaScript, the figures on screen could quietly disagree
with the tested Python.

**Decision.** The page filters, but it never restates a formula. Python computes every
measure per row and groups it to the finest grain the report needs
(`reporting/cube.py`); the page only sums, subtracts, averages and divides those
measures. Where a *rule* rather than a formula decides grouping, the payload carries
the answer Python worked out, for the same reason.

- `store × article × day` carries units, revenue, cost and line count. Revenue and cost
  are already after discount and at purchase price, so every sales KPI is a sum, gross
  margin is one subtraction of two sums, and margin % is a ratio of sums.
- `store × week` carries cost of goods sold and inventory value. Turnover picks the
  weeks lying entirely inside the range — the rule from
  [0004](0004-inventory-turnover-from-inventory-file.md) — then divides summed COGS by
  mean weekly value, as `kpis.inventory.inventory_turnover` does.
- `store × day` carries possible returns, so that tile narrows with the rest.
- `store × week` also carries the sales-against-inventory reconciliation, so that table
  narrows to the weeks turnover used.
- A day → week and month lookup carries which Monday starts each day's week and which
  calendar month it falls in. `enrich_sales` decides both; the page reads them rather
  than recomputing them from the date, which is the one place a rule could otherwise
  have drifted. It is also what keeps filtering cheap — see below.

**The date controls span what the facts cover, not what the sales cover.** An inventory
week counts towards turnover only when it lies entirely inside the range, so the last
selectable day reaches the end of the last inventory week rather than the last sale
(`cube.date_bounds`). Otherwise, on a run whose range ended after the last clean sale,
the page's own full selection would drop a week the server-rendered report included, and
Reset would disagree with the figures it replaced.

Stores and regions are both multi-select dropdowns — a disclosure button over a
checkbox list, with All and None — rather than native `<select multiple>` listboxes,
which need ctrl-click and lose the whole selection on a stray click. Both start at
"All". The two apply together: a store counts when it is ticked *and* its region is
ticked, so narrowing the regions greys out the stores it excludes while remembering
their ticks. The Articles tab has its own control for the ranking measure, showing one
of revenue, gross margin or gross margin % at a time, because six lists at once buried
the one being looked at.

**Measures keep full precision in the payload.** Rounding them to 2dp rounds *before*
summing, and across 10,789 rows that moved gross margin to 10,301,981 against the
pipeline's 10,301,980. Full precision costs about 50 KB and removes the whole class of
error; the browser test now asserts gross margin in TRY, which is the figure that
exposed it.

**Data quality does not filter.** Validation runs on the full input files before any
filter, so the data-quality tab and the masthead strip describe the whole file for every
selection. The filter bar says so, and a test asserts the totals do not move.

**Consequences.** The payload adds about 0.3 MB to a 4.7 MB file — the report is 5.0 MB,
still one self-contained offline file. The CLI filters keep their meaning: they decide
what the report covers, and the in-page controls narrow within it. With scripting off
the filter bar is hidden and the server-rendered full-selection report remains correct.

Correctness is held by a new seam, agreed for this change and recorded in `CLAUDE.md`:
`tests/test_report_filters.py` drives the real controls in a real browser and compares
what is on screen with figures from `tools/profile_selections.py`, a standalone pandas
script over `data/` that shares no code with the pipeline. Three independent routes —
the pipeline, the page, and that script — agree on all four selections tested, for the
six masthead measures, for the by-week and by-month tables, and for inventory turnover
per store. The unscripted page is checked too: with JavaScript off the filter bar is
hidden and the server-rendered figures are the full-selection ones.

An undefined ratio — turnover with no inventory value, margin % with no revenue — prints
as an em dash on both sides. Python produced `inf` or `nan` and the page produced `0.00`,
which disagreed about a figure that has no value.

**What this costs at a size we do not have.** `design-session.md` settles that 2 MB of
CSV makes performance irrelevant, and it does — the whole pipeline runs in 0.7 s. But the
page's cost is per fact row and per store, so it is worth knowing where it stops working.
Measured on generated data with the same defect mix, at 1,000 stores over 7 regions
(5.8M transactions, a 127 MB report): a filter change took 5.1 s, of which about 90% of
the aggregation was building a `Date` per fact row to find its week and month. Reading
both from the day lookup instead — the same change the drift argument above already
wanted — brought a filter change to 1.8 s. Of what is left, roughly 1.1 s is Plotly
relaying out one bar per store: three charts, 34,000 px tall. Capping those at a top-N
would be the next thing to do, and it changes what the report shows, so it is not done
here. Beyond that the grain itself is the limit: `store × article × day` compresses
28,060 rows into 10,789 today (2.6:1) but 5.7M into 3.7M at 1,000 stores (1.5:1), because
a fact row approaches one per transaction as cardinality grows. At that size the article
dimension would have to leave the page, which is a different decision from this one.
