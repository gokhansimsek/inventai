# 0002 — Rules as small classes in an ordered registry

**Context.** pandera validates types and value checks well, but this pipeline also
needs to repair values, date rows from other rows, check references against tables
validated moments earlier, and flag rows without removing them, with a reason on
every affected row. Encoding all of that as pandera checks would bend the library
out of shape.

**Decision.** pandera coerces column types (`CoerceToSchema`). Every other check is a
small class satisfying the `Rule` protocol: `rule_id`, `table`, `severity`,
`description`, and `apply(df, tables) -> RuleResult`. Generic rules are configured
by table and column, e.g. `RejectOutOfRange("transactions", "discount_pct", 0, 100)`.
`validation/registry.py` lists them in execution order; the engine runs them and
collects counts, quarantined rows and flagged rows.

Order is part of the design: master data before the tables that reference it (so
rejecting a store rejects its sales), exact copies before type coercion, and key
conflicts after row-level checks (so the one valid version of a conflicting row is
kept).

**Consequences.** Adding a check is one class and one registry line, and each rule is
tested alone on a tiny table. The data-quality report is generated from the rules
themselves, so it cannot drift from the code. The cost is a hand-maintained order,
documented at the top of the registry.
