"""
Test script: run the three BI queries against C2M and print results.
READ-ONLY: Only SELECT statements are executed; no database changes.

Usage (from repo root with venv active and .env set):
  python -m pipeline.test_queries

Use this to verify that the governed SQL returns the expected data before
running the full pipeline (which adds the AI narrative step).
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv

load_dotenv()


def main() -> None:
    if not os.getenv("ORACLE_USER") or not os.getenv("ORACLE_PASSWORD") or not os.getenv("ORACLE_DSN"):
        print("Set ORACLE_USER, ORACLE_PASSWORD, and ORACLE_DSN in .env to run query tests.")
        sys.exit(1)

    from fetch_usage import fetch_bi_summary_with_raw

    print("Running BI queries (read-only SELECT)...")
    print("-" * 60)
    metrics, df_arrears, df_duplicate, df_bankruptcy = fetch_bi_summary_with_raw()

    print("1. Strategic Arrears Summary")
    print(f"   Rows: {len(df_arrears)}")
    if not df_arrears.empty:
        print("   Columns:", list(df_arrears.columns))
        print("   First rows:")
        print(df_arrears.head().to_string(index=False))
    else:
        print("   (No rows returned)")
    print()

    print("2. Duplicate Payment Detection")
    print(f"   Rows: {len(df_duplicate)}")
    if not df_duplicate.empty:
        print("   Columns:", list(df_duplicate.columns))
        print("   First rows:")
        print(df_duplicate.head().to_string(index=False))
    else:
        print("   (No rows returned)")
    print()

    print("3. Bankruptcy Monitor")
    print(f"   Rows: {len(df_bankruptcy)}")
    if not df_bankruptcy.empty:
        print("   Columns:", list(df_bankruptcy.columns))
        print("   First rows:")
        print(df_bankruptcy.head().to_string(index=False))
    else:
        print("   (No rows returned)")
    print()

    print("Aggregated metrics (passed to AI narrative):")
    print("-" * 60)
    for k, v in metrics.items():
        print(f"  {k}: {v}")
    print()
    print("Done. No database changes were made (SELECT only).")


if __name__ == "__main__":
    main()
