# Architecture decision records

Short records of the decisions that shape the code: the context, the choice, and
what it costs. The full design discussion is in [../design-session.md](../design-session.md).

| ADR | Decision |
|---|---|
| [0001](0001-fix-reject-flag-validation.md) | Every data issue is fixed, rejected or flagged; nothing is dropped silently |
| [0002](0002-rules-as-small-classes.md) | Validation rules are small classes in an ordered registry, with pandera for types |
| [0003](0003-validate-before-filtering.md) | Validate the full input before applying any filter |
| [0004](0004-inventory-turnover-from-inventory-file.md) | Inventory turnover uses the inventory file alone |
| [0005](0005-date-future-transactions-from-id-order.md) | Future-dated transactions are dated from transaction id order |
| [0006](0006-report-model-and-writers.md) | One report model, rendered by HTML and CSV writers |
| [0007](0007-report-hierarchy-and-tabs.md) | The report leads with a persistent masthead and splits its sections into tabs |
| [0008](0008-in-report-filtering.md) | The report filters itself from pre-aggregated facts; no KPI formula is restated in the page |
