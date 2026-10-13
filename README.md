# ChoiceQR Orders Pipeline

**Python + BigQuery restaurant-order ingestion, SQL deduplication, and analytics quality checks**

[![Python checks](https://github.com/veletnap17/choiceqr-orders-pipeline/actions/workflows/python-checks.yml/badge.svg)](https://github.com/veletnap17/choiceqr-orders-pipeline/actions/workflows/python-checks.yml)

A portfolio adaptation of a restaurant analytics integration. It demonstrates how order data can move from a paginated REST API into BigQuery, then become usable for reporting and decision-making across multiple restaurant locations.

## Business problem

Restaurant operations and marketing analysis depend on consistent order data: revenue trends, cancellations, first-time buyers, and location-level performance. API data may arrive in multiple pages, be re-fetched in overlapping windows, or contain later updates to existing orders. A useful analytics pipeline needs to ingest that data reliably and define how duplicates are handled before reporting.

## What this repository demonstrates

- **API ingestion:** retrieves archived orders from the ChoiceQR API for three configured locations
- **Incremental extraction:** fetches a rolling two-day window to capture recent orders and updates
- **Resilience:** handles pagination, HTTP errors, and bounded retries for HTTP 429 responses
- **Cloud data loading:** flattens JSON with pandas and appends records to a BigQuery raw table
- **SQL transformations:** example BigQuery `MERGE` using `(restaurant, _id)` as the deduplication key
- **Analytics:** sample daily order, revenue, cancellation, and first-order queries
- **Verification:** Python unit tests, GitHub Actions checks, and a synthetic BigQuery SQL regression script

## Architecture

```text
             ChoiceQR REST API
             3 restaurant locations
                      |
              Python (main.py)
          pagination / retries / JSON
                      |
             BigQuery raw orders
                 WRITE_APPEND
                      |
               BigQuery SQL
          deduplication + QA checks
                      |
           Analytical query examples
        revenue / orders / cancellations
```

**Repository scope:** `main.py` currently loads **raw data only**. BigQuery SQL scripts are separate examples; this repository does **not** automatically orchestrate them. The screenshots illustrate a Cloud Run deployment, but deployment and scheduling configuration are not included. This public copy contains no production credentials.

## Technology

Python 3.10+ · requests · pandas · Google BigQuery · Standard SQL · GitHub Actions

## Quick start

1. Install dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

2. Configure Google Cloud Application Default Credentials with BigQuery permissions and set environment variables:

   | Environment variable | Use |
   | --- | --- |
   | `PROJECT_ID` | Required GCP project |
   | `TOKEN_VINOHRADY`, `TOKEN_ZIZKOV`, `TOKEN_CHODOV` | ChoiceQR API tokens for each location |
   | `DATASET` | BigQuery dataset (default `Data_total`) |
   | `RAW_TABLE` | Raw destination table (default `orders_all_raw`) |
   | `MAX_PAGES`, `PER_PAGE`, `SLEEP_SECONDS`, `MAX_RETRIES` | Optional request settings |

3. Run ingestion:

   ```bash
   python main.py
   ```

No API tokens or GCP credentials are provided. The pipeline requires access to a ChoiceQR account and your own BigQuery project/dataset.

## Repository map

| File | Purpose |
| --- | --- |
| [`main.py`](main.py) | API extraction and append-only BigQuery loading |
| [`tests/test_main.py`](tests/test_main.py) | HTTP and pagination unit tests |
| [`sql/deduplicate_orders.sql`](sql/deduplicate_orders.sql) | Example composite-key BigQuery `MERGE` |
| [`sql/daily_metrics.sql`](sql/daily_metrics.sql) | Daily revenue, orders, and cancellations |
| [`sql/first_time_customers.sql`](sql/first_time_customers.sql) | First order date by customer phone |
| [`sql/data_quality_checks.sql`](sql/data_quality_checks.sql) | Post-merge duplicate/null-key assertions |
| [`sql/tests/synthetic_bigquery_regression.sql`](sql/tests/synthetic_bigquery_regression.sql) | Independent regression demo with temporary tables |
| [`.github/workflows/python-checks.yml`](.github/workflows/python-checks.yml) | Python test workflow |

## Test the project

**Python unit tests (no live API calls):**

```bash
python -m unittest discover -s tests -v
```

The [GitHub Actions workflow](.github/workflows/python-checks.yml) runs these checks on pull requests and pushes to `main`.

**BigQuery SQL regression demo:** paste the complete contents of [`sql/tests/synthetic_bigquery_regression.sql`](sql/tests/synthetic_bigquery_regression.sql) into the BigQuery SQL editor and run it as one script. It creates **temporary tables with synthetic orders**, then asserts:

- latest order updates replace older versions
- the same order ID at different restaurants remains distinct
- null business keys are ignored
- repeated `MERGE` execution is idempotent for the sample
- sample daily revenue, order counts, and cancellation counts match expectations

The regression script was **executed successfully in BigQuery by the project owner**. This validates the synthetic scenario, **not** compatibility with an arbitrary production schema. The demo repeats the transformation logic rather than importing the main SQL files; GitHub Actions does not execute BigQuery SQL.

## Data model and caveats

The ingestion table stores raw API data with `restaurant` and `loaded_at` metadata. The deduplication example uses `(restaurant, _id)` and prefers the latest `timestamps_created` and `loaded_at`, with deterministic tie-breaking. This composite key is a **design assumption** to verify against actual ChoiceQR identifier semantics.

SQL scripts use `project_id` placeholders; adapt table paths and verify data types, schemas, and required target columns before executing against real tables. The illustrative `MERGE` updates/inserts only five specified columns and assumes other target fields are nullable or have defaults.

The sample daily-metrics query sums the `total` field across all statuses (including cancellations); whether cancelled orders should contribute to **business revenue** depends on the source's accounting conventions. The first-order query uses customer phone as the identifier, which may not uniquely identify one customer.

## Evidence / screenshots

**Raw orders in BigQuery**

![Raw orders table](screenshots/orders_all_raw.png)

**Deduplicated orders in BigQuery**

![Deduplicated orders table](screenshots/orders_all_dedup.png)

**Cloud Run deployment screenshot**

![Cloud Run deployment](screenshots/cloud_run.png)

## Future work

Add reproducible cloud deployment and scheduling; automate SQL transforms and schema validation; expand monitoring, reconciliation, and freshness checks; and test business metric definitions against approved source data.

---

**Author:** Ruslan Panteleev
