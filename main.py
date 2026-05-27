import os
import time
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
from google.cloud import bigquery


BASE_URL = "https://open-api.choiceqr.com"

PROJECT_ID = os.getenv("PROJECT_ID")
DATASET = os.getenv("DATASET", "Data_total")

RAW_TABLE = os.getenv("RAW_TABLE", "orders_all_raw")
DEDUP_TABLE = os.getenv("DEDUP_TABLE", "orders_all_dedup")

MAX_PAGES = int(os.getenv("MAX_PAGES", 1000))
PER_PAGE = int(os.getenv("PER_PAGE", 100))
SLEEP_SECONDS = int(os.getenv("SLEEP_SECONDS", 6))


RESTAURANTS = {
    "Vinohrady": {
        "restaurant": "Vinohrady",
        "token": os.getenv("TOKEN_VINOHRADY"),
    },
    "Zizkov": {
        "restaurant": "Zizkov",
        "token": os.getenv("TOKEN_ZIZKOV"),
    },
    "Chodov": {
        "restaurant": "Chodov",
        "token": os.getenv("TOKEN_CHODOV"),
    },
}


def fetch_orders_for_restaurant(restaurant_name, token, date_from, date_till):
    all_orders = []

    if not token:
        print(f"Skipping {restaurant_name}: token is missing")
        return all_orders

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    page = 1

    while page <= MAX_PAGES:
        params = {
            "from": date_from,
            "till": date_till,
            "page": page,
            "perPage": PER_PAGE,
        }

        response = requests.get(
            f"{BASE_URL}/orders/list/archive",
            headers=headers,
            params=params,
            timeout=60,
        )

        if response.status_code == 429:
            print(f"{restaurant_name}: rate limit, sleeping...")
            time.sleep(10)
            continue

        if response.status_code == 400:
            print(f"{restaurant_name}: no more pages or bad request on page {page}")
            break

        response.raise_for_status()

        data = response.json()

        orders = data.get("orders", data if isinstance(data, list) else [])

        if not orders:
            break

        for order in orders:
            order["restaurant"] = restaurant_name
            order["loaded_at"] = datetime.now(timezone.utc).isoformat()

        all_orders.extend(orders)

        print(f"{restaurant_name}: loaded page {page}, rows: {len(orders)}")

        page += 1
        time.sleep(SLEEP_SECONDS)

    return all_orders


def load_to_bigquery(df, table_name):
    client = bigquery.Client(project=PROJECT_ID)

    table_id = f"{PROJECT_ID}.{DATASET}.{table_name}"

    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_APPEND",
        autodetect=True,
    )

    job = client.load_table_from_dataframe(
        df,
        table_id,
        job_config=job_config,
    )

    job.result()

    print(f"Loaded {len(df)} rows into {table_id}")


def run_pipeline():
    date_till = datetime.now(timezone.utc).date()
    date_from = date_till - timedelta(days=2)

    date_from = date_from.isoformat()
    date_till = date_till.isoformat()

    final_orders = []

    for restaurant_key, restaurant_config in RESTAURANTS.items():
        orders = fetch_orders_for_restaurant(
            restaurant_name=restaurant_config["restaurant"],
            token=restaurant_config["token"],
            date_from=date_from,
            date_till=date_till,
        )

        final_orders.extend(orders)

    if not final_orders:
        print("No orders found")
        return

    df = pd.json_normalize(final_orders)

    load_to_bigquery(df, RAW_TABLE)


if __name__ == "__main__":
    run_pipeline()
