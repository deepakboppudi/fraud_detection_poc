# main.py
"""
Multi-Agent Financial Fraud Detective — POC (Minimal API calls)
===============================================================
Flow:
  BigQuery (one query)
    → Bot A: ADK Agent calls detect_fraud() once
      → Bot B: One Gemini call to write SAR report

Only 2 Gemini API calls total:
  1. Bot A reasons over the tool result
  2. Bot B writes the SAR report
"""

import os
import json
import asyncio
from datetime import datetime

from google.cloud import bigquery
from google.adk.agents import LlmAgent
from google.adk.runners import InMemoryRunner
from google.adk.tools import FunctionTool
from google.genai import types

import config

bq_client = bigquery.Client(project=config.GCP_PROJECT)
os.makedirs(config.REPORT_OUTPUT_DIR, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLE TOOL — one BigQuery query that detects all fraud patterns at once
# ═══════════════════════════════════════════════════════════════════════════════

def detect_fraud() -> str:
    """
    Run a single BigQuery query to detect all fraud patterns at once.
    Combines smurfing, geo risk, and velocity into one SQL call.
    """
    print("[Tool] Running BigQuery fraud detection query...")

    # Smurfing — transactions just below $10,000 BSA threshold
    query = f"""
        SELECT
            'SMURFING'       AS pattern,
            account,
            COUNT(*)         AS txn_count,
            ROUND(SUM(amount), 2) AS total_amount,
            'HIGH'           AS risk,
            '31 U.S.C. 5324 - Structuring' AS law
        FROM `{config.BQ_TABLE_REF}`
        WHERE amount BETWEEN {config.SMURFING_LOWER} AND {config.SMURFING_UPPER}
        GROUP BY account
        HAVING txn_count >= 3

        UNION ALL

        SELECT
            'GEO_RISK'       AS pattern,
            account,
            COUNT(*)         AS txn_count,
            ROUND(SUM(amount), 2) AS total_amount,
            'HIGH'           AS risk,
            'FATF Recommendation 10 - Enhanced Due Diligence' AS law
        FROM `{config.BQ_TABLE_REF}`
        WHERE country IN ('PA', 'KY', 'BZ', 'NG', 'RU')
        GROUP BY account
        HAVING txn_count >= 1

        ORDER BY total_amount DESC
    """

    rows = [dict(r) for r in bq_client.query(query).result()]

    if not rows:
        return json.dumps({"status": "clean", "findings": []})

    print(f"[Tool] Found {len(rows)} suspicious patterns in BigQuery.")
    return json.dumps({"status": "suspicious", "findings": rows})


# ═══════════════════════════════════════════════════════════════════════════════
# BOT A — ADK Investigator Agent (1 tool, 1 Gemini call)
# ═══════════════════════════════════════════════════════════════════════════════

async def run_bot_a() -> list:
    print("=" * 50)
    print("BOT A - Investigator Agent")
    print("=" * 50)

    bot_a = LlmAgent(
        name="fraud_investigator",
        model=config.GEMINI_MODEL,
        tools=[FunctionTool(detect_fraud)],
        instruction=(
            "You are a fraud investigator. "
            "Call detect_fraud() once, then return the findings as a JSON array. "
            "Return only the JSON array from the findings field, nothing else."
        ),
    )

    runner  = InMemoryRunner(agent=bot_a, app_name="fraud_detective")
    session = await runner.session_service.create_session(
        app_name="fraud_detective",
        user_id="system"
    )

    print(f"\n[Bot A] Querying {config.BQ_TABLE_REF}...")

    findings = []
    async for event in runner.run_async(
        user_id="system",
        session_id=session.id,
        new_message=types.Content(
            role="user",
            parts=[types.Part(text="Run fraud detection now.")]
        ),
    ):
        if event.is_final_response():
            text = event.content.parts[0].text.strip()
            try:
                start = text.find("[")
                end   = text.rfind("]") + 1
                if start != -1 and end > start:
                    findings = json.loads(text[start:end])
            except (json.JSONDecodeError, IndexError):
                pass

    print(f"[Bot A] Done — {len(findings)} patterns found.")
    for f in findings:
        print(f"  [{f.get('risk')}] {f.get('pattern')} "
              f"- {f.get('account')}: {f.get('txn_count')} txns, "
              f"${f.get('total_amount'):,}")
    return findings


# ═══════════════════════════════════════════════════════════════════════════════
# BOT B — ADK Compliance Reporter (no tools, 1 Gemini call)
# ═══════════════════════════════════════════════════════════════════════════════

async def run_bot_b(findings: list) -> str:
    print("\n" + "=" * 50)
    print("BOT B - Compliance Reporter Agent")
    print("=" * 50)

    bot_b = LlmAgent(
        name="compliance_reporter",
        model=config.GEMINI_MODEL,
        instruction=(
            "You are a financial compliance officer. "
            "Write a short formal SAR report with: "
            "1. Summary 2. Findings 3. Laws Violated 4. Actions. "
            "Be concise — under 300 words."
        ),
    )

    runner  = InMemoryRunner(agent=bot_b, app_name="fraud_detective")
    session = await runner.session_service.create_session(
        app_name="fraud_detective",
        user_id="system"
    )

    print(f"\n[Bot B] Generating SAR with {config.GEMINI_MODEL}...")

    sar = ""
    async for event in runner.run_async(
        user_id="system",
        session_id=session.id,
        new_message=types.Content(
            role="user",
            parts=[types.Part(text=(
                f"Write SAR report for these findings:\n{json.dumps(findings, indent=2)}"
            ))]
        ),
    ):
        if event.is_final_response():
            sar = event.content.parts[0].text

    return sar


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

async def main():
    print("\n FRAUD DETECTIVE POC")
    print(f" Project : {config.GCP_PROJECT}")
    print(f" Table   : {config.BQ_TABLE_REF}")
    print(f" Model   : {config.GEMINI_MODEL}")
    print(f" Total Gemini calls: 2 (one per agent)\n")

    # Step 1: Bot A — one BQ query + one Gemini call
    findings = await run_bot_a()

    if not findings:
        print("\n[Main] No fraud detected. Exiting.")
        return

    # Step 2: Bot B — one Gemini call to write SAR
    sar = await run_bot_b(findings)

    # Step 3: Save and print
    print("\n" + "=" * 50)
    print("GENERATED SAR REPORT")
    print("=" * 50)
    print(sar)

    filename = os.path.join(
        config.REPORT_OUTPUT_DIR,
        f"SAR_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    )
    with open(filename, "w") as f:
        f.write(sar)
    print(f"\n[Main] Saved -> {filename}")


if __name__ == "__main__":
    asyncio.run(main())