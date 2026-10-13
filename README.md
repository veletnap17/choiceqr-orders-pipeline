# ChoiceQR Orders Pipeline

Portfolio version of a restaurant orders ingestion pipeline built with Python, the ChoiceQR REST API, and Google BigQuery.

## Overview

The Python script retrieves archived orders for three configured restaurant locations, handles pagination and basic rate limits, normalizes the API responses, and appends records to a BigQuery raw table. Separate SQL examples demonstrate deduplication and reporting for business analytics.

> **Scope:** `main.py` implements API-to-BigQuery raw ingestion. The SQL scripts are not invoked automatically by the Python script. Deployment and scheduling configuration are not included in this portfolio repository.

## Technologies

Python · pandas · requests · SQL · Google BigQuery · Google Cloud Run (example screenshot)

## Architecture

```text
ChoiceQR REST API (3 locations)
             |
       Python / main.py
             |
     BigQuery raw orders
             |
  SQL transformations (separate)
             |
 Deduplicated and analytical data
```

## Setup

Requires Python 3.10+, an accessible ChoiceQR API account, a Google Cloud project and BigQuery permissions.

```bash
python -m pip install -r requirements.txt
```

Set the following environment variables (do not commit real tokens):

| Variable | Description |
| --- | --- |
| `PROJECT_ID` | Google Cloud project ID (required) |
| `DATASET` | BigQuery dataset, default `Data_total` |
| `TOKEN_VINOHRADY` | ChoiceQR token for Vinohrady |
| `TOKEN_ZIZKOV` | ChoiceQR token for Zizkov |
| `TOKEN_CHODOV` | ChoiceQR token for Chodov |
| `RAW_TABLE` | BigQuery raw table, default `orders_all_raw` |
| `MAX_PAGES`, `PER_PAGE`, `SLEEP_SECONDS` | Optional API pagination and pacing settings |

Authenticate to Google Cloud using Application Default Credentials, then run:

```bash
python main.py
```

The script loads a rolling two-day date range. It requires real API credentials and access to the target BigQuery dataset, so this repository is not directly runnable without configuration.

## Files

```text
main.py
config.example.py
requirements.txt
sql/
  daily_metrics.sql
  deduplicate_orders.sql
  first_time_customers.sql
screenshots/
  orders_all_raw.png
  orders_all_dedup.png
  cloud_run.png
```

## Analytics examples

- Daily orders, revenue and cancelled orders by restaurant
- First order date by customer phone number
- Deduplication with BigQuery `MERGE`

**Note:** SQL scripts use `project_id` placeholders; replace them and validate schemas before execution. The example `MERGE` and its deduplication key need review before production use.

## Screenshots

**BigQuery raw orders**

![Raw orders](screenshots/orders_all_raw.png)

**BigQuery deduplicated orders**

![Deduplicated orders](screenshots/orders_all_dedup.png)

**Cloud Run deployment**

![Cloud Run](screenshots/cloud_run.png)

## Improvements planned

- Robust HTTP error handling and bounded 429 retries
- More reliable cross-location deduplication and schema checks
- Automated tests and data quality checks
- Scheduling, orchestration, monitoring and CI/CD

## Author

Ruslan Panteleev
