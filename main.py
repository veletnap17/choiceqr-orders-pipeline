import os
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests
from google.cloud import bigquery

BASE_URL = "https://open-api.choiceqr.com"
PROJECT_ID = os.getenv("PROJECT_ID")
DATASET = os.getenv("DATASET", "Data_total")
RAW_TABLE = os.getenv("RAW_TABLE", "orders_all_raw")
MAX_PAGES = int(os.getenv("MAX_PAGES", "1000"))
PER_PAGE = int(os.getenv("PER_PAGE", "100"))
SLEEP_SECONDS = float(os.getenv("SLEEP_SECONDS", "6"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))

RESTAURANTS = {
    "Vinohrady": os.getenv("TOKEN_VINOHRADY"),
    "Zizkov": os.getenv("TOKEN_ZIZKOV"),
    "Chodov": os.getenv("TOKEN_CHODOV"),
}


def fetch_orders_for_restaurant(restaurant_name, token, date_from, date_till, session=None):
    if not token:
        print(f"Skipping {restaurant_name}: missing token")
        return []

    session = session or requests
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    all_orders = []

    for page in range(1, MAX_PAGES + 1):
        params = {"from": date_from, "till": date_till, "page": page, "perPage": PER_PAGE}
        for attempt in range(MAX_RETRIES + 1):
            response = session.get(f"{BASE_URL}/orders/list/archive", headers=headers, params=params, timeout=60)
            if response.status_code == 429:
                if attempt == MAX_RETRIES:
                    raise RuntimeError(f"{restaurant_name}: rate limit persisted after {MAX_RETRIES} retries (page {page})")
                retry_after = response.headers.get("Retry-After", "")
                try:
                    delay = min(max(float(retry_after), 0), 60)
                except (TypeError, ValueError):
                    delay = min(2 ** attempt, 60)
                print(f"{restaurant_name}: rate limited on page {page}; retrying in {delay:g}s")
                time.sleep(delay)
                continue
            response.raise_for_status()
            break

        data = response.json()
        if isinstance(data, dict):
            orders = data.get("orders", [])
        elif isinstance(data, list):
            orders = data
        else:
            raise ValueError(f"{restaurant_name}: unexpected API response type on page {page}")
        if not isinstance(orders, list):
            raise ValueError(f"{restaurant_name}: orders must be a list on page {page}")
        if not orders:
            break

        loaded_at = datetime.now(timezone.utc).isoformat()
        for order in orders:
            if not isinstance(order, dict):
                raise ValueError(f"{restaurant_name}: invalid order on page {page}")
            all_orders.append({**order, "restaurant": restaurant_name, "loaded_at": loaded_at})
        print(f"{restaurant_name}: page {page}: {len(orders)} orders")
        if page < MAX_PAGES:
            time.sleep(SLEEP_SECONDS)

    return all_orders


def load_to_bigquery(df, table_name):
    if not PROJECT_ID:
        raise ValueError("PROJECT_ID environment variable is required")
    client = bigquery.Client(project=PROJECT_ID)
    table_id = f"{PROJECT_ID}.{DATASET}.{table_name}"
    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND", autodetect=True)
    client.load_table_from_dataframe(df, table_id, job_config=job_config).result()
    print(f"Loaded {len(df)} rows into {table_id}")


def run_pipeline():
    date_till = datetime.now(timezone.utc).date()
    date_from = date_till - timedelta(days=2)
    all_orders = []
    for restaurant, token in RESTAURANTS.items():
        all_orders.extend(fetch_orders_for_restaurant(restaurant, token, date_from.isoformat(), date_till.isoformat()))
    if not all_orders:
        print("No orders found")
        return
    load_to_bigquery(pd.json_normalize(all_orders), RAW_TABLE)


if __name__ == "__main__":
    run_pipeline()
