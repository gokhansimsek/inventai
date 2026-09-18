# 0007 — A persistent masthead and tabbed sections in the HTML report

**Context.** The report was one 8,000-pixel scroll of eight equally-weighted sections.
Four identical grey tiles gave revenue and "possible returns" the same visual weight,
so nothing said which number was the headline and which was a problem. Severity —
the heart of the validation contract — was a lowercase word in a table, and the whole
data-quality section sat near the bottom, below four sales sections. The numbers were
right; the page did not say what mattered.

**Decision.** Presentation only: the `Report` model and the writer interface from
[0006](0006-report-model-and-writers.md) are unchanged, and the extra totals the page
needs are computed in `writers.py`, not added to the model.

- A **masthead** that stays on screen for every tab: revenue as a single hero figure,
  three supporting stats, and a data-quality strip carrying the fix/flag/reject totals
  and the reconciliation line (`raw = clean + quarantined`) with the run's real numbers.
- The sections become five **tabs** — Sales, Articles, Inventory, Data quality,
  Assumptions — as a `tablist` with `aria-selected`, roving `tabindex` and arrow-key
  navigation. Panels are open in the markup and JavaScript hides all but one, so with
  scripting off the page degrades to the previous full scroll rather than to one
  section. Printing and `beforeprint` reopen every panel.
- **Status colour is reserved for genuine status.** Severities render as a coloured dot
  beside the word, never the word alone, because the warning step does not clear text
  contrast on this surface. Revenue and margin get no good/bad colour — there is no
  target in the data to judge them against — so the hero carries emphasis instead.

**Consequences.** The first screen now answers "how did we do, and can I trust the
data" without scrolling; the default tab is Sales and data quality is one click away
rather than six sections down. Plotly lays a chart out against its container's width,
so a chart drawn inside a hidden panel has none and is resized when its tab is first
shown. The file stays a single self-contained offline HTML; tabs add no network use.
Charts still sit beside their tables, and every value remains reachable with the tabs
collapsed, in print, and in the CSV outputs.
