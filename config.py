# config.py
"""
All configuration for the Fraud Detective POC.
Fill in your GCP values below or set them as environment variables.
"""

import os
from dotenv import load_dotenv

load_dotenv()  # reads .env file if present

# ── GCP Project ───────────────────────────────────────────────────────────────
GCP_PROJECT    = os.getenv("GCP_PROJECT")   # ← change this
GCP_LOCATION   = os.getenv("GCP_LOCATION")

# ── BigQuery ──────────────────────────────────────────────────────────────────
BQ_DATASET     = os.getenv("BQ_DATASET")
BQ_TABLE       = os.getenv("BQ_TABLE")

# Full table reference used in queries
BQ_TABLE_REF   = f"{GCP_PROJECT}.{BQ_DATASET}.{BQ_TABLE}"

# ── Gemini ────────────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")                    # ← change this
GEMINI_MODEL   = os.getenv("GEMINI_MODEL")

# ── Fraud Detection Thresholds ────────────────────────────────────────────────
BSA_CTR_THRESHOLD  = 10_000
SMURFING_LOWER     = 9_000
SMURFING_UPPER     = 9_999
VELOCITY_THRESHOLD = 10          # max transactions allowed per hour
HIGH_RISK_COUNTRIES = ["PA", "KY", "BZ", "NG", "RU", "IR", "KP"]

# ── Report Output ─────────────────────────────────────────────────────────────
REPORT_OUTPUT_DIR  = os.getenv("REPORT_OUTPUT_DIR", "reports")