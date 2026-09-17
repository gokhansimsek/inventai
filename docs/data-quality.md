# Data Quality

What the pipeline checks, what it found in the provided data, and how each issue
is handled. Every figure below comes from a pipeline run on `data/` and is
confirmed by an independent pandas profile (see `tests/test_pipeline.py`).

## How issues are handled

Each check is a rule with one of three outcomes:

| Outcome | Meaning | Where the rows go |
|---|---|---|
| **Fix** | Provably recoverable: an exact rule, or evidence that holds across the whole file | Corrected in place; count reported |
| **Reject** | Unusable for any KPI | `quarantine/<table>.csv`, with `reason` and `rule_id` |
| **Flag** | Suspicious but usable | Kept in the analysis, and recorded in `issues/<table>.csv` |

Nothing is dropped silently: for every table, **raw rows = clean rows + quarantined
rows**. Validation always runs on the full files, before any store, region or date
filter, so the data-quality results are the same for every run.

A structurally broken input (missing file, missing column) stops the run
instead: no number computed from it could be trusted.

## Row counts

| Table | Raw | Clean | Quarantined |
|---|---:|---:|---:|
| stores | 5 | 5 | 0 |
| articles | 200 | 200 | 0 |
| transactions | 28,890 | 28,060 | 830 |
| inventory | 1,326 | 1,326 | 0 |

## Issues found

### Transactions

| Issue | Rows | Outcome | Evidence and handling |
|---|---:|---|---|
| Exact copies of an earlier row | 138 | Reject | Identical in every column; first copy kept. |
| Same `transaction_id`, different content | 5 ids | Resolved | In all 5, the rows differ only in the sign of `quantity` (e.g. `+1` and `-1`). The negative copy fails the quantity check, leaving one valid row, which is kept. The conflict check runs after the row-level checks for exactly this reason. |
| Missing `customer_id` spelled four ways | 2,292 | Fix | Blank, `N/A`, `NULL`, `NA` all mean "no value"; stored as null. Missing customers are expected (walk-ins) and are not an error. |
| Dates in `DD-MM-YYYY` | 1,396 | Fix | Read as day-first: many have a first part above 12 and none has a second part above 12. |
| Dates in the future (2027) | 15 | Fix + Flag | Transaction ids increase with date across all 28,875 other rows, so each takes the date of the preceding id (all become 2024-03-31). Flagged with the original date. If ids were not in date order, these rows would be quarantined instead. The 15 rows are also all `Sunny` with no discount, which suggests injected records. |
| Prices in kurus (`KRS`) | 4,324 | Fix | KRS prices are exactly 100x TRY prices for the same articles; divided by 100. |
| Quantity zero or negative | 577 | Reject | Values -1 to -5. They may be returns, but nothing links them to an original sale; reported as possible returns. |
| Unknown store `S-099` | 115 | Reject | Not in `stores.csv`. |

### Stores

| Issue | Rows | Outcome | Handling |
|---|---:|---|---|
| `S-004` opening date `2027-03-15` | 1 | Flag | Impossible, and S-004 has sales in March 2024. No KPI uses opening date, so the store and its 26% of sales are kept. |
| Region names differ from the brief | all | Assumption | The brief lists North/South/East/West/Central; the file uses Turkish regions (Marmara, Aegean, Central Anatolia, Mediterranean). The file's values are used, including for `--region`. |

### Articles

| Issue | Rows | Outcome | Handling |
|---|---:|---|---|
| Purchase price above recommended selling price | 4 | Flag | Loses money at the recommended price; may be deliberate, so kept. |

### Inventory

| Issue | Rows | Outcome | Handling |
|---|---:|---|---|
| Stock does not balance (opening + received - sold != closing) | 28 | Flag | Off by 1 to 10 units. Kept, using the reported stock levels. |
| `sold_qty` does not match sales in `transactions.csv` | — | Reported | Inventory covers 497 store-article pairs, sales cover 1,038, and weekly quantities do not reconcile. Inventory turnover is computed from the inventory file alone. |

## Checks that found nothing

Run on every execution, so a future file with these problems is caught:

- Exact copies in stores, articles, inventory; key conflicts in every table.
- Values that do not parse as their column type.
- Unknown articles in transactions and inventory; unknown stores in inventory.
- Non-positive area, purchase price, recommended price or selling price;
  discount outside 0–100; negative stock quantities.
- Unexpected currency or store type.
- **Price outliers:** a sale priced more than 50% away from the article's
  recommended price (configurable as `price_tolerance`). None found: after the
  KRS fix, every price is within ±5% of the recommended price. Quantities range
  1 to 5, so no quantity outliers either.
