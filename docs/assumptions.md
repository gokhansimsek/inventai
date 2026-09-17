# Assumptions

Where the data or the brief is ambiguous, these are the readings the pipeline
uses. Data issues and their handling are in [data-quality.md](data-quality.md);
design choices are in [adr/](adr/).

## Money

- **All amounts are TRY.** `KRS` prices are kuruş and are divided by 100: for
  the same articles, KRS prices are exactly 100x TRY prices.
- **Revenue is after discount:** quantity × selling price × (1 − discount_pct / 100).
  `discount_pct` is a percentage from 0 to 100.
- **Cost is today's purchase price.** `articles.csv` has one purchase price per
  article and no history, so every sale is costed at it.
- **Gross margin % = (revenue − cost) / revenue.** It is also reported in TRY,
  because a percentage alone ranks a tiny article above a large one.

## Sales

- **Negative quantities are not revenue.** They may be returns, but none is
  linked to an original sale. They are quarantined and totalled as
  *possible returns* (576 lines, 1,036 units, 1,179,763 TRY for the full data),
  shown beside revenue rather than subtracted from it.
- **Future-dated transactions belong to the end of the data.** Transaction ids
  increase with date everywhere else, so each takes the date of the preceding
  id (see [ADR 0005](adr/0005-date-future-transactions-from-id-order.md)).
- **A missing `customer_id` is a walk-in,** not an error, as the brief says.
- **Sales at stores missing from `stores.csv` are excluded** (`S-099`), including
  from possible returns, so every figure covers the same stores.
- **"Future" means after the run date** (`as_of`, default today), so the rules
  still hold for data from other periods.

## Stores

- **Regions are the values in `stores.csv`** (Marmara, Aegean, Central Anatolia,
  Mediterranean), not the North/South/East/West/Central listed in the brief.
  `--region` uses these values.
- **S-004's opening date (2027-03-15) is wrong but harmless:** no KPI uses it and
  the store trades throughout March 2024, so it is flagged, not excluded.

## Time

- **Weeks run Monday to Sunday.** The data starts on Friday 1 March and ends on
  Sunday 31 March 2024, so the first week in weekly figures is partial (3 days).
- **Date filters are inclusive** of both ends.
- **Monthly revenue** is computed by calendar month; the provided data has one.

## Inventory

- **A snapshot row describes one week,** starting on its date (a Monday):
  opening stock, receipts and sales during the week, closing stock.
- **Snapshots are independent samples.** Each store-week covers a different
  subset of articles, and closing stock does not carry into the next week's
  opening stock (3 of 667 consecutive pairs match). Figures therefore take
  sales and stock from the same rows and never chain weeks together.
- **Inventory turnover is for the period, not annualised,** and describes the
  sampled articles (see [ADR 0004](adr/0004-inventory-turnover-from-inventory-file.md)).
- **Only whole weeks inside the date range count** for turnover. A range with no
  whole week reports turnover as not available rather than a partial figure.
- **Inventory rows that do not balance are used as reported** (28 rows, off by
  1 to 10 units): stock levels are observations; the arithmetic is the suspect part.

## Rankings

- **Top/bottom lists hold 10 articles** (`top_n`).
- **Margin % rankings need at least 20 units sold** (`min_units_for_margin_pct`).
  Chain-wide every article clears this; it matters for narrow selections such as
  one store on one day.
