"""
Orchestrate: fetch usage -> generate narrative -> write JSON for Jasper.
Run from repo root or pipeline/:  python -m pipeline.main   or   python pipeline/main.py
Use --mock to run without a usage CSV (for testing Gemini and JSON output).
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Allow running as script or module
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv

from fetch_usage import fetch_usage_and_summarize, fetch_bi_summary, validate_data_health
from fetch_usage import _oracle_available
from generate_narrative import generate_narrative, generate_bi_narrative, generate_business_snapshot

load_dotenv()

MOCK_SUMMARY = {
    "current_amount": 150.0,
    "prior_amount": 120.0,
    "amount_delta": 30.0,
    "percent_change": 25.0,
    "current_usage_kwh": 450.0,
    "prior_usage_kwh": 380.0,
    "heatwave_days": 5,
}


def run_pipeline(
    usage_csv_path: str | Path | None = None,
    output_path: str | Path | None = None,
    mock: bool = False,
) -> dict:
    """
    Fetch data, generate AI narrative, write JSON.
    When Oracle is available and not mock: runs BI queries (arrears, payment integrity, bankruptcy)
    and generates a Senior BI Analyst narrative. Otherwise uses usage/CSV and billing narrative.
    Returns the dict written to disk (narrative + all metrics for Jaspersoft JSONQL).
    """
    if mock:
        summary = MOCK_SUMMARY
        narrative = generate_narrative(
            current_amount=summary["current_amount"],
            prior_amount=summary["prior_amount"],
            heatwave_days=summary.get("heatwave_days", 0),
            amount_delta=summary.get("amount_delta", 0),
            percent_change=summary.get("percent_change", 0),
        )
        out = {
            "narrative": narrative,
            "business_snapshot": generate_business_snapshot(summary),
            "current_amount": summary["current_amount"],
            "prior_amount": summary["prior_amount"],
            "amount_delta": summary.get("amount_delta", 0),
            "percent_change": summary.get("percent_change", 0),
        }
    elif _oracle_available():
        if not validate_data_health():
            narrative = (
                "Data validation failed: core C2M tables appear empty or stale. "
                "No summary generated. Verify that CI_FT, CI_SA, and related tables "
                "contain current data (e.g. CRE_DTTM within the last 7 days)."
            )
            out = {
                "narrative": narrative,
                "business_snapshot": narrative,
                "total_debt": 0, "debt_30_days": 0, "debt_60_days": 0, "debt_over_60": 0,
                "large_bill_count": 0, "duplicate_payment_account_count": 0,
                "duplicate_payment_example_amt": 0, "bankruptcy_alert_count": 0, "bankruptcy_pym_amt": 0,
            }
        else:
            metrics = fetch_bi_summary()
            narrative = generate_bi_narrative(metrics)
            business_snapshot = generate_business_snapshot(metrics)

            # Workstream insights and value proposition for Jaspersoft
            workstream_insights = []
            try:
                health_path = Path(__file__).resolve().parent.parent / "output" / "workstream_health.json"
                if health_path.exists():
                    with open(health_path, encoding="utf-8") as f:
                        h = json.load(f)
                    ws = h.get("workstreams") or {}
                    # Field Ops data currency risk
                    fo = ws.get("field_ops") or {}
                    if fo.get("date_col") and fo.get("count_7d") == 0:
                        workstream_insights.append("Field Operations: no new CI_SP installs in the last 7 days (data currency risk).")
            except Exception:
                pass
            try:
                cfg_path = Path(__file__).resolve().parent.parent / "output" / "config_completeness.json"
                if cfg_path.exists():
                    with open(cfg_path, encoding="utf-8") as f:
                        cfg = json.load(f)
                    rules = (cfg or {}).get("rules") or {}
                    gap = rules.get("billing_gap_60d") or {}
                    if isinstance(gap.get("count"), int) and gap.get("count", 0) > 0:
                        workstream_insights.append(
                            f"Debt Management: {gap['count']} active service agreements have no financial transactions in the last 60 days (billing gap)."
                        )
                    # F1 Metadata Layer: Batch Health Critical Path Risk
                    batch_health = rules.get("batch_health_critical_path") or {}
                    if batch_health.get("critical_path_risk") is True:
                        failures = batch_health.get("count", 0)
                        workstream_insights.append(
                            f"Critical Path Risk: {failures} batch failure(s) in the last 24 hours (Billing/Finance/Payment batches). Revenue operations may be impacted."
                        )
            except Exception:
                pass

            out = {
                "narrative": narrative,
                "business_snapshot": business_snapshot,
                "workstream_insights": " ".join(workstream_insights) if workstream_insights else "",
                "value_proposition": (
                    "This automated audit combines arrears, payment integrity, billing gaps, and operational recency "
                    "into a single view, reducing manual reconciliation effort and highlighting go-live and ongoing risks."
                ),
                **metrics,
            }
    else:
        summary = fetch_usage_and_summarize(usage_csv_path)
        narrative = generate_narrative(
            current_amount=summary["current_amount"],
            prior_amount=summary["prior_amount"],
            heatwave_days=summary.get("heatwave_days", 0),
            amount_delta=summary.get("amount_delta", 0),
            percent_change=summary.get("percent_change", 0),
        )
        out = {
            "narrative": narrative,
            "business_snapshot": generate_business_snapshot(summary),
            "workstream_insights": "",
            "value_proposition": (
                "This automated usage summary reduces manual effort by turning monthly billing and weather effects "
                "into a concise story for customers and staff."
            ),
            "current_amount": summary["current_amount"],
            "prior_amount": summary["prior_amount"],
            "amount_delta": summary.get("amount_delta", 0),
            "percent_change": summary.get("percent_change", 0),
        }

    # Audit metadata for Jaspersoft "Audit Metadata" band (Senior Auditor visibility)
    meta_path = Path(__file__).resolve().parent.parent / "output" / "validation_metadata.json"
    try:
        if meta_path.exists():
            with open(meta_path, encoding="utf-8") as f:
                meta = json.load(f)
            last_run = meta.get("last_run_utc") or "N/A"
            orphan = meta.get("orphan_sa_count")
            orphan_txt = str(orphan) if orphan is not None else "N/A"
            latency = "Risk flagged" if meta.get("system_latency_risk") else "OK"
            out["validation_summary"] = (
                f"Audit: validation run {last_run}; "
                f"Orphan SAs (active, no arrears rows): {orphan_txt}. System latency: {latency}."
            )
        else:
            out["validation_summary"] = "Audit: validation_metadata.json not found. Run python -m pipeline.validate_tables."
    except Exception:
        out["validation_summary"] = "Audit: validation metadata unavailable."

    path = output_path or os.getenv("NARRATIVE_JSON_PATH", "output/narrative.json")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate bill narrative JSON for Jasper.")
    parser.add_argument("--mock", action="store_true", help="Use mock usage data (no CSV).")
    parser.add_argument("--csv", type=str, default=None, help="Path to usage CSV (overrides env).")
    parser.add_argument("--output", type=str, default=None, help="Output JSON path (overrides env).")
    args = parser.parse_args()
    run_pipeline(
        usage_csv_path=args.csv,
        output_path=args.output,
        mock=args.mock,
    )
