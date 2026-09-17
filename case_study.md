# Retail Analytics Case Study

## Overview

Welcome to the retail analytics case study. You have been provided with datasets
representing 1 month of operations for a multi-format retail chain operating
5 stores across Turkey. Your task is to build a **Python-based analytics
pipeline** that ingests this data, validates and cleans it, computes key business
metrics, and produces a summary report.

This case study is designed to evaluate your:

- Analytical and problem-solving skills
- Ability to design modular, maintainable systems
- Written communication and documentation skills
- Technical proficiency with Python data tools

## Dataset Description

You have been provided with four data files in the `data/` directory:

### `data/stores.csv`

Store master data for the retail chain.

| Column | Description |
|--------|-------------|
| `store_id` | Unique store identifier (e.g., `S-001`) |
| `store_name` | Human-readable store name |
| `city` | City where the store is located |
| `region` | Geographic region (North, South, East, West, Central) |
| `store_type` | Format: Hypermarket, Supermarket, Express |
| `opening_date` | Date when the store opened |
| `area_sqft` | Store area in square feet |

### `data/articles.csv`

Article (product) master data.

| Column | Description |
|--------|-------------|
| `article_id` | Unique article identifier (e.g., `ART-00001`) |
| `article_name` | Product name |
| `category` | Product category |
| `sub_category` | Product sub-category |
| `brand` | Brand name |
| `purchase_price` | Cost price paid to supplier |
| `recommended_selling_price` | Recommended retail price |

### `data/transactions.csv`

Daily sales transactions (~29K rows).

| Column | Description |
|--------|-------------|
| `transaction_id` | Unique transaction identifier |
| `date` | Date of transaction |
| `store_id` | Store where the transaction occurred |
| `article_id` | Article sold |
| `quantity` | Number of units sold |
| `selling_price` | Actual selling price per unit |
| `currency` | Currency code for the selling price |
| `discount_pct` | Discount percentage applied |
| `customer_id` | Customer identifier (may be missing for walk-ins) |
| `weather_condition` | Weather at time of sale |

### `data/inventory.csv`

Weekly inventory snapshots (~1.2K rows).

| Column | Description |
|--------|-------------|
| `date` | Snapshot date |
| `store_id` | Store identifier |
| `article_id` | Article identifier |
| `opening_stock` | Stock at start of week |
| `received_qty` | Units received during the week |
| `sold_qty` | Units sold during the week |
| `closing_stock` | Stock at end of week |

## Important

**This case study is intentionally open-ended.** The requirements below set the
direction, but how you design, structure, and implement your solution is up to
you. We value thoughtful engineering decisions over exhaustive feature coverage.

**Use your professional judgment to:**

- Decide what data quality checks are necessary before computation
- Choose the right level of abstraction and modularity
- Prioritize which KPIs provide the most business value
- Make assumptions where the data is ambiguous — and document them

Think of this as building a real analytics system that a retail operations team
will rely on. What would make it trustworthy, maintainable, and useful?

## Requirements

### 1. Data Validation & Cleaning

Before computing any metrics, your pipeline should validate the input data and
handle quality issues appropriately. Consider:

- Referential integrity between files
- Data type consistency and format standardization
- Outlier detection and handling
- Completeness checks
- Any other checks you deem necessary

**Document what issues you find and how you handle them.**

### 2. KPI Computation

Compute the following business metrics. You may add additional metrics if you
find them valuable.

| KPI | Description | Granularity |
|-----|-------------|-------------|
| Revenue | Total sales value (after discounts) | Store, Category, Monthly |
| Gross Margin | (Revenue - Cost) / Revenue | Store, Category |
| Top/Bottom Articles | Ranked by revenue and margin | Top 10 / Bottom 10 |
| Inventory Turnover | Cost of Goods Sold / Average Inventory | Store |

### 3. Output Report

Produce a summary report that a business stakeholder could review. The format
is your choice (CSV, Excel with multiple sheets, HTML, PDF, etc.).

### 4. Configurability

The system should support at minimum:

- Running for a specific store, region, or all stores
- Configurable date range for analysis

How you expose this configuration (CLI arguments, config file, function
parameters) is your design decision.

## Constraints

- **Python only** — any libraries/packages are allowed
- **No external services** — the pipeline should run locally with just the data files
- Assume the data files are in a `data/` directory relative to your code

## Deliverables

Please provide:

1. **Working Code** (Required)
   - A Python project that can be run to produce the output report
   - Clear instructions for running (README with setup and execution steps)
   - All source code and configuration

2. **Output Report** (Required)
   - The actual output produced by running your pipeline on the provided data
   - Should demonstrate the KPIs listed above

3. **Assumptions & Decisions Document** (Required)
   - What data quality issues did you find?
   - What assumptions did you make?
   - What design decisions did you make and why?

4. **Tests** (Encouraged)
   - Unit tests for critical computation logic
   - Data validation tests

## Technical Guidelines

- Structure your code as you would a production project
- Consider how someone else would read, run, and extend your code
- Use appropriate logging
- Handle errors gracefully

### Use of AI Tools

You are encouraged to use AI tools and agents (ChatGPT, Claude, Copilot, etc.)
to assist with your work. If you do, include a brief **AI Usage Log** as part
of your submission covering:

1. **What you used** — Which tools/models, and for what parts (code generation, debugging, design, etc.)
2. **Human refinement** — How did you edit, iterate, or improve on the AI output?
3. **Challenges** — Did you encounter issues like hallucinations, incorrect suggestions, or bad patterns? How did you verify and fix them?
4. **Overall reflection** — Estimate the ratio of AI-generated vs. human-crafted content in your final submission (e.g., "40% AI / 60% Human"). Did using AI reveal any blind spots or change your original approach?

**We view AI tools as part of a modern engineer's toolkit.** Using them well
(with good prompts, critical review of output, and proper integration) is a
positive signal. Blindly accepting AI output without understanding or testing
is not.

## Evaluation Criteria

Your submission will be evaluated on:

1. **Data Quality Handling**
2. **System Design & Modularity**
3. **Code Quality**
4. **Analytical Correctness**
5. **Communication**
6. **Pragmatism**

## Time Expectation

This case study is designed to take approximately **4–6 hours** to complete.
We value quality over quantity — focus on demonstrating your engineering skills
and thought process rather than covering every possible edge case.

## Submission Instructions

Please submit your completed work as either:

- A Git repository (preferred — we'd like to see commit history)
- A compressed archive (ZIP or TAR.GZ)

Include a README file at the root with clear setup and run instructions.

## Questions?

If you have any questions about the requirements or encounter issues with the
dataset, please reach out to your recruiting contact.

Good luck!

---

*Note: This is a synthetic dataset designed to simulate real-world retail data
with realistic patterns and imperfections. The data quality issues are
intentional and part of the evaluation.*
