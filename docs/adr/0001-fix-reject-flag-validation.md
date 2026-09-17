# 0001 — Fix, reject or flag; nothing dropped silently

**Context.** The data has intentional quality problems of very different kinds:
some are provably recoverable (KRS prices, day-first dates), some make a row
unusable (negative quantity, unknown store), and some are suspicious but affect no
KPI (a store's future opening date). A batch job for an operations team should not
stop on one bad row, and should not quietly lose rows either.

**Decision.** Every rule has one of three outcomes:

- **Fix** only when recovery is provable from an exact rule or from evidence that
  holds across the whole file. The count is reported.
- **Reject** rows unusable for any KPI into `quarantine/<table>.csv` with a
  `reason` and `rule_id`.
- **Flag** suspicious but usable rows: they stay in the analysis and are written
  to `issues/<table>.csv` for review.

For every table, raw = clean + rejected; a test asserts it on the real data.
Structural problems (missing file or column, invalid config) stop the run instead,
because no number computed from them could be trusted.

**Consequences.** Revenue is always reconcilable with the input, and a reviewer can
open the quarantine file to see exactly what was left out and why. The cost is a
judgement per rule about which outcome is right; those judgements are recorded in
[../data-quality.md](../data-quality.md).
