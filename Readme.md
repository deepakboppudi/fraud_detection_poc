# Multi-Agent Financial Fraud Detective
### GCP Architect POC — Built with BigQuery + ADK + Gemini 2.5 Pro

A multi-agent AI pipeline that automatically detects financial fraud patterns
in banking transactions and generates a formal compliance report — built using
real Google Cloud services.

---

## Architecture

```
On-Prem Database (SQLite simulation)
        │
        │  setup_bigquery.py  ← one-time ETL load
        ▼
┌─────────────────────────────────────┐
│  BigQuery                           │
│  Dataset : fraud_detection          │
│  Table   : transactions             │
│  231 rows, partitioned by day       │
└─────────────────┬───────────────────┘
                  │  UNION ALL SQL query
                  ▼
┌─────────────────────────────────────┐
│  Bot A — ADK LlmAgent               │
│  Role   : Financial Investigator    │
│  Tool   : detect_fraud()            │
│  Brain  : Gemini 2.5 Pro            │
└─────────────────┬───────────────────┘
                  │  Findings JSON
                  ▼
┌─────────────────────────────────────┐
│  Bot B — ADK LlmAgent               │
│  Role   : Compliance Reporter       │
│  Tool   : None (pure LLM writing)   │
│  Brain  : Gemini 2.5 Pro            │
└─────────────────┬───────────────────┘
                  │
                  ▼
        reports/SAR_<timestamp>.txt
        (Suspicious Activity Report)
```

---

## GCP Services Used

| Service | Purpose |
|---|---|
| **BigQuery** | Cloud data warehouse — stores and queries transactions |
| **Gemini 2.5 Pro** | Powers both ADK agents (Bot A and Bot B) |
| **Google ADK 0.2.0** | Agent orchestration framework |

---

## Fraud Patterns Detected

| Pattern | What It Means | Law |
|---|---|---|
| **Smurfing** | Multiple transactions between $9,000–$9,999 — just below the $10,000 BSA mandatory reporting threshold | 31 U.S.C. § 5324 — Structuring |
| **Geo Risk** | Wire transfers to FATF high-risk jurisdictions — Panama, Cayman Islands, Belize, Nigeria, Russia | FATF Recommendation 10 — Enhanced Due Diligence |

---

## Project Structure

```
fraud_detection_poc/
├── main.py               # Full pipeline — Bot A + Bot B
├── setup_bigquery.py     # One-time BigQuery table creation + data seed
├── config.py             # All settings, reads from .env
├── models.py             # Lists Gemini models available for your API key
├── requirements.txt      # Python dependencies
├── env.sample            # Rename to .env and fill in your values
└── reports/              # SAR reports saved here (auto-created on run)
```

---

## Prerequisites

- Python 3.11 or higher
- GCP account (free tier works)
- Gemini 2.5 Pro API key from [aistudio.google.com](https://aistudio.google.com)
- Google Cloud SDK (`gcloud`) installed

---

## Setup & Run

### Step 1 — Clone the repository
```bash
git clone https://github.com/your-username/fraud-detection-poc.git
cd fraud-detection-poc
```

### Step 2 — Create and activate virtual environment
```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Mac / Linux
source .venv/bin/activate
```

### Step 3 — Install dependencies
```bash
pip install -r requirements.txt
```

### Step 4 — Configure environment
```bash
# Windows
copy env_example.txt .env

# Mac / Linux
cp env_example.txt .env
```

Edit `.env` and fill in your values:
```env
GCP_PROJECT=your-gcp-project-id
GEMINI_API_KEY=AIzaSy...
GEMINI_MODEL=gemini-2.5-pro
REPORT_OUTPUT_DIR=reports
```

> To find your GCP project ID:
> ```bash
> gcloud config get-value project
> ```

> To verify which models your API key supports:
> ```bash
> python check_models.py
> ```

### Step 5 — Authenticate with GCP
```bash
gcloud auth application-default login
```
A browser window will open — sign in with the Google account that has access to your GCP project.

### Step 6 — Create BigQuery table and seed data
> Run this **once only** before the first demo run.

```bash
python setup_bigquery.py
```

Expected output:
```
[SETUP] Creating BigQuery dataset and table...
[BQ] Dataset ready: your-project.fraud_detection
[BQ] Table ready: your-project.fraud_detection.transactions

[SETUP] Seeding transaction data (simulates on-prem DB sync)...
[BQ] Loaded 231 rows via load job (free tier compatible)
[BQ] Successfully loaded 231 rows

[SETUP] Done. Now run: python main.py
```

### Step 7 — Run the pipeline
```bash
python main.py
```

Expected output:
```
 FRAUD DETECTIVE POC
 Project : your-project
 Table   : your-project.fraud_detection.transactions
 Model   : gemini-2.5-pro
 Total Gemini calls: 2

==================================================
BOT A - Investigator Agent
==================================================
[Bot A] Querying your-project.fraud_detection.transactions...
[Tool] Running BigQuery fraud detection query...
[Tool] Found 4 suspicious patterns in BigQuery.
[Bot A] Done — 4 patterns found.
  [HIGH] SMURFING - ACC-001: 10 txns, $93,754.00
  [HIGH] GEO_RISK - ACC-002: 6 txns, $79,753.00

==================================================
BOT B - Compliance Reporter Agent
==================================================
[Bot B] Generating SAR with gemini-2.5-pro...

==================================================
GENERATED SAR REPORT
==================================================

SUSPICIOUS ACTIVITY REPORT
...Gemini 2.5 Pro generated formal SAR here...

[Main] Saved -> reports/SAR_20260323_120000.txt
```

---

## API Quota

This POC makes exactly **2 Gemini API calls** per run:

1. **Bot A** — one call to reason over BigQuery tool results
2. **Bot B** — one call to generate the SAR report

### Gemini 2.5 Pro Free Tier Limits

| Limit | Value |
|---|---|
| Requests per minute | 5 |
| Requests per day | 25 |
| Input tokens per minute | 250,000 |

> If you hit `429 RESOURCE_EXHAUSTED`, wait a few minutes and retry.
> For higher limits, add billing to your GCP project
> (uses free $300 credits — you will not be charged).

---

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `403 Streaming insert not allowed` | Free tier blocks streaming inserts | Fixed — uses `load_table_from_json()` |
| `ModuleNotFoundError: deprecated` | Missing ADK dependency | `pip install deprecated==1.2.14` |
| `TypeError: bytes not JSON serializable` | Bug in ADK 0.1.0 telemetry | Fixed — upgraded to `google-adk==0.2.0` |
| `'coroutine' has no attribute 'id'` | `create_session` is async in ADK 0.2.0 | Fixed — added `await` |
| `429 RESOURCE_EXHAUSTED` | Gemini free tier quota exhausted | Wait 24h or use new API key |
| `404 Model not found` | Wrong model name format | Run `python check_models.py` |
| `gcloud not authenticated` | GCP auth expired | Run `gcloud auth application-default login` |
| `BQ table not found` | Setup not run yet | Run `python setup_bigquery.py` |

---

## Tech Stack

| Layer | Local Simulation | Real GCP Service |
|---|---|---|
| On-prem database | SQLite seed script | Cloud SQL (PostgreSQL) |
| Data warehouse | BigQuery | BigQuery |
| Agent framework | Google ADK 0.2.0 | Google ADK 0.2.0 |
| LLM | Gemini 2.5 Pro | Gemini 2.5 Pro (Enterprise) |
| Report storage | Local `reports/` folder | Cloud Storage bucket |

---

## License

MIT
