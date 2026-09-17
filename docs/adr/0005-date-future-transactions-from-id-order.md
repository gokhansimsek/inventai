# 0005 — Date future transactions from id order

**Context.** 15 transactions are dated January–February 2027 in a March 2024 dataset.
The first plan was to quarantine them, but discarding real sales without trying to
recover them was rejected. Profiling then showed that `transaction_id` order matches
date order across all 28,875 other rows, and the 15 ids follow directly after the
last March sale.

**Decision.** A transaction dated after the run date takes the date of the transaction
with the closest earlier id, and is flagged with its original date. The rule checks
the id/date ordering on the current data every run; if it does not hold, future-dated
rows are quarantined instead of guessed.

**Consequences.** The 15 sales count, dated 2024-03-31, and the change is visible in
`issues/transactions.csv`. The inferred date is the earliest possible date for those
sales, not a certainty; the report states the assumption.
