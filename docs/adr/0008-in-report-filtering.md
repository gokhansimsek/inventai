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
(`reporting/cube.py`); the page only sums, averages and divides those measures.

- `store × article × day` carries units, revenue, cost and line count. Revenue and cost
  are already after discount and at purchase price, so every sales KPI is a sum, and
  margin % is a ratio of sums.
- `store × week` carries cost of goods sold and inventory value. Turnover picks the
  weeks lying entirely inside the range — the rule from
  [0004](0004-inventory-turnover-from-inventory-file.md) — then divides summed COGS by
  mean weekly value, as `kpis.inventory.inventory_turnover` does.
- `store × day` carries possible returns, so that tile narrows with the rest.

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

Correctness is held by a new seam, agreed for this change: `tests/test_report_filters.py`
drives the real controls in a real browser and compares what is on screen with figures
from a standalone pandas script over `data/`, not from the pipeline. Three independent
routes — the pipeline, the page, and that script — agree on all four selections tested.
