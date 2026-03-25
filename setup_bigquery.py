# setup_bigquery.py
"""
One-time setup script.
Run this ONCE before main.py to:
  1. Create the BigQuery dataset and table
  2. Seed it with simulated on-prem transaction data (normal + fraud patterns)

Usage:
    python setup_bigquery.py

Requires:
    gcloud auth application-default login
    OR set GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
"""

import random
from datetime import datetime, timedelta, timezone
from google.cloud import bigquery
import config

# BigQuery client
client = bigquery.Client(project=config.GCP_PROJECT)


def create_dataset():
    """Create BQ dataset if it doesn't exist."""
    dataset_id = f"{config.GCP_PROJECT}.{config.BQ_DATASET}"
    dataset    = bigquery.Dataset(dataset_id)
    dataset.location = config.GCP_LOCATION

    client.create_dataset(dataset, exists_ok=True)
    print(f"[BQ] Dataset ready: {dataset_id}")


def create_table():
    """Create transactions table with schema."""
    schema = [
        bigquery.SchemaField("txn_id",    "STRING",    mode="REQUIRED"),
        bigquery.SchemaField("account",   "STRING",    mode="REQUIRED"),
        bigquery.SchemaField("amount",    "FLOAT64",   mode="REQUIRED"),
        bigquery.SchemaField("country",   "STRING",    mode="REQUIRED"),
        bigquery.SchemaField("timestamp", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("flag",      "STRING",    mode="REQUIRED"),
    ]

    table = bigquery.Table(config.BQ_TABLE_REF, schema=schema)

    # Partition by day — cost-efficient for large transaction tables
    table.time_partitioning = bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY,
        field="timestamp"
    )

    client.create_table(table, exists_ok=True)
    print(f"[BQ] Table ready: {config.BQ_TABLE_REF}")


def seed_data():
    """
    Generate transaction data and load into BigQuery using a load job.

    NOTE: We use load_table_from_json() instead of insert_rows_json()
    because streaming inserts are NOT supported on the GCP free tier.
    Load jobs are free and supported on all account types.
    """
    random.seed(42)
    rows = []
    accounts = ["ACC-001", "ACC-002", "ACC-003", "ACC-004", "ACC-005"]

    # Normal transactions
    for i in range(200):
        ts = datetime.now(timezone.utc) - timedelta(
            days=random.randint(0, 30),
            hours=random.randint(0, 23)
        )
        rows.append({
            "txn_id":    f"TXN-{i:04d}",
            "account":   random.choice(accounts),
            "amount":    round(random.uniform(50, 4000), 2),
            "country":   random.choice(["US", "US", "US", "DE", "GB"]),
            "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "flag":      "NORMAL",
        })

    # Fraud Pattern 1: Smurfing (ACC-001)
    # 10 transfers just below $10,000 BSA threshold — classic structuring
    for i in range(10):
        ts = datetime.now(timezone.utc) - timedelta(days=i)
        ts = ts.replace(hour=10, minute=0, second=0, microsecond=0)
        rows.append({
            "txn_id":    f"TXN-SMURF-{i}",
            "account":   "ACC-001",
            "amount":    round(random.uniform(config.SMURFING_LOWER,
                                              config.SMURFING_UPPER), 2),
            "country":   "US",
            "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "flag":      "SMURFING",
        })

    # Fraud Pattern 2: High-risk jurisdiction wires (ACC-002)
    # Wires to Panama, Cayman Islands, Belize — FATF grey list countries
    for i in range(6):
        ts = datetime.now(timezone.utc) - timedelta(days=i * 2)
        ts = ts.replace(hour=14, minute=0, second=0, microsecond=0)
        rows.append({
            "txn_id":    f"TXN-GEO-{i}",
            "account":   "ACC-002",
            "amount":    round(random.uniform(5000, 20000), 2),
            "country":   random.choice(["PA", "KY", "BZ"]),
            "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "flag":      "GEO_RISK",
        })

    # Fraud Pattern 3: Velocity (ACC-003)
    # 15 transactions within a single hour — account takeover signal
    base_time = datetime.now(timezone.utc).replace(
        hour=9, minute=0, second=0, microsecond=0
    )
    for i in range(15):
        ts = base_time + timedelta(minutes=i * 3)
        rows.append({
            "txn_id":    f"TXN-VEL-{i}",
            "account":   "ACC-003",
            "amount":    round(random.uniform(200, 2000), 2),
            "country":   "US",
            "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "flag":      "HIGH_VELOCITY",
        })

    # Load into BigQuery via load job (free tier compatible)
    # WRITE_TRUNCATE = overwrite existing data, safe to re-run
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
    )

    print(f"[BQ] Loading {len(rows)} rows via load job (free tier compatible)...")
    load_job = client.load_table_from_json(
        rows,
        config.BQ_TABLE_REF,
        job_config=job_config,
    )
    load_job.result()  # wait for job to complete

    print(f"[BQ] Successfully loaded {len(rows)} rows into {config.BQ_TABLE_REF}")


if __name__ == "__main__":
    print("\n[SETUP] Creating BigQuery dataset and table...")
    create_dataset()
    create_table()

    print("\n[SETUP] Seeding transaction data (simulates on-prem DB sync)...")
    seed_data()

    print("\n[SETUP] Done. Now run: python main.py\n")