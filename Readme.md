# Multi-Agent Financial Fraud Detective
### GCP Architect POC — Option 1

A multi-agent AI pipeline that detects financial fraud in banking transactions using **Google BigQuery**, **Google ADK**, and **Gemini** — built as a proof of concept

---

## Architecture

```
On-Prem Database (SQLite seed)
        │
        │  setup_bigquery.py (one-time ETL load)
        ▼
BigQuery — fraud_detection.transactions
        │
        │  Single UNION ALL query
        ▼
Bot A — ADK LlmAgent (Investigator)
   └── Tool: detect_fraud()
        │
        │  Findings JSON
        ▼
Bot B — ADK LlmAgent (Compliance Reporter)
   └── Gemini generates formal SAR report
        │
        ▼
reports/SAR_<timestamp>.txt
```

---

## GCP Services Used

| Service | Purpose |
|---|---|
| **BigQuery** | Data warehouse — stores and queries transactions |
| **Gemini** (`gemini-2.0-flash`) | Powers both ADK agents |
| **ADK** (Agent Development Kit) | Orchestrates Bot A and Bot B |

---

## Fraud Patterns Detected

| Pattern | Detection Logic | Law |
|---|---|---|
| **Smurfing** | Transactions between $9,000–$9,999 (just below BSA $10K CTR threshold) | 31 U.S.C. § 5324 |
| **Geo Risk** | Wire transfers to FATF high-risk jurisdictions (PA, KY, BZ, NG, RU) | FATF Recommendation 10 |

---

## Project Structure

```
fraud_detection_poc/
├── main.py               # Pipeline — Bot A + Bot B
├── setup_bigquery.py     # One-time BQ table creation + data seed
├── config.py             # All settings (reads from .env)
├── check_models.py       # Lists Gemini models available for your API key
├── requirements.txt      # Python dependencies
├── .env.example          # Environment variable template
└── reports/              # Generated SAR reports (auto-created)
```

---

## Setup & Run

### Prerequisites
- Python 3.11+
- GCP account (free tier works)
- Gemini API key from [aistudio.google.com](https://aistudio.google.com)

### 1. Clone and install
```bash
git clone https://github.com/your-username/fraud-detection-poc.git
cd fraud-detection-poc
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Mac/Linux
pip install -r requirements.txt
```

### 2. Authenticate with GCP
```bash
gcloud auth application-default login
```

### 3. Configure environment
```bash
cp .env.example .env
```

Edit `.env` and fill in:
```env
GCP_PROJECT=your-gcp-project-id
GEMINI_API_KEY=AIzaSy...
GEMINI_MODEL=gemini-2.0-flash
```

> **Find your project ID:**
> ```bash
> gcloud config get-value project
> ```

> **Find valid model names for your key:**
> ```bash
> python check_models.py
> ```

### 4. Create BigQuery table and seed data (run once)
```bash
python setup_bigquery.py
```

Expected output:
```
[BQ] Dataset ready: your-project.fraud_detection
[BQ] Table ready: your-project.fraud_detection.transactions
[BQ] Loaded 231 rows into your-project.fraud_detection.transactions
```

### 5. Run the pipeline
```bash
python main.py
```

Expected output:
```
FRAUD DETECTIVE POC
 Project : your-project
 Table   : your-project.fraud_detection.transactions
 Model   : gemini-2.0-flash

BOT A - Investigator Agent
[Bot A] Querying your-project.fraud_detection.transactions...
[Tool] Running BigQuery fraud detection query...
[Tool] Found 4 suspicious patterns in BigQuery.
[Bot A] Done — 4 patterns found.
  [HIGH] SMURFING - ACC-001: 10 txns, $93,754.00
  [HIGH] GEO_RISK - ACC-002: 6 txns, $79,753.00

BOT B - Compliance Reporter Agent
[Bot B] Generating SAR with gemini-2.0-flash...

GENERATED SAR REPORT
================================================
...SAR report printed here...

[Main] Saved -> reports/SAR_20260323_120000.txt
```

---

## API Quota Notes

This POC makes **exactly 2 Gemini API calls** per run to stay within free tier limits:

1. **Bot A** — one call to reason over BigQuery tool results
2. **Bot B** — one call to generate the SAR report

### Free Tier Limits

| Model | Requests/day | Requests/min |
|---|---|---|
| gemini-2.0-flash | 200 | 15 |
| gemini-1.5-flash | 1,500 | 15 |

If you hit a `429 RESOURCE_EXHAUSTED` error:
- Wait 24 hours for daily quota to reset, **or**
- Add billing to your GCP project (uses free $300 credits, not charged), **or**
- Create a new GCP project with a fresh API key

---

## Known Issues & Fixes

| Error | Fix |
|---|---|
| `403 Streaming insert is not allowed` | Fixed — uses `load_table_from_json()` instead of `insert_rows_json()` |
| `ModuleNotFoundError: deprecated` | Run `pip install deprecated==1.2.14` |
| `TypeError: bytes is not JSON serializable` | Fixed — upgrade to `google-adk==0.2.0` |
| `AttributeError: 'coroutine' object has no attribute 'id'` | Fixed — `create_session` is async in ADK 0.2.0, uses `await` |
| `429 RESOURCE_EXHAUSTED` | Free tier quota hit — wait 24h or add billing |
| `404 Model not found` | Run `python check_models.py` to find valid model names for your key |

---
