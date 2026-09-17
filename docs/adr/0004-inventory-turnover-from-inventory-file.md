# 0004 — Inventory turnover from the inventory file alone

**Context.** Turnover = cost of goods sold / average inventory. COGS could come from
the transactions or from the inventory file's `sold_qty`. The two do not agree:
inventory covers 497 store-article pairs while sales cover 1,038, and weekly
quantities for the same pairs differ widely. Snapshots also sample different
articles each week, and closing stock does not carry into the next week's opening.

**Decision.** Compute turnover from the inventory file only, so COGS and stock come
from the same rows: COGS = Σ `sold_qty` × purchase price; average inventory = mean
over weeks of Σ (opening + closing) / 2 × purchase price. Only weeks entirely inside
the date range count. The result is for the period, not annualised. The report shows
the weeks used and a like-for-like comparison of inventory `sold_qty` with
transaction units for the same store, article and week.

**Consequences.** The ratio is internally consistent, and the disagreement between the
files is reported rather than hidden. Turnover describes the sampled articles, not
the whole assortment, and a date range shorter than a full week yields no turnover.
