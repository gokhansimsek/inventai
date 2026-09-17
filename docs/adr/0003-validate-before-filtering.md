# 0003 — Validate the full input before filtering

**Context.** Users run the pipeline for a store, a region or a date range. If filters
ran first, a narrow selection would hide data problems (a date range excluding the
2027-dated rows would never see them), and the data-quality section would change
from run to run.

**Decision.** Validation always runs on the complete input files. Store, region and
date filters apply afterwards, to clean data only. Unknown stores or regions in a
filter stop the run with the list of valid values. A selection with no sales is a
valid result: the report says so and still shows inventory and data quality.

**Consequences.** The data-quality section is identical for every selection, and a
problem in the input is reported whatever is selected. A narrow run still does the
full validation work, which is negligible at this data size.
