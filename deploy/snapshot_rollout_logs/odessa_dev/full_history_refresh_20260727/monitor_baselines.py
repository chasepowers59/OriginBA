#!/usr/bin/env python3
"""Poll Odessa DEV 3-stream baseline jobs until all leave RUNNING."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
LOGDIR = Path(__file__).resolve().parent
DONE = Path("/tmp/odessa_baselines_done")
PROGRESS = LOGDIR / "03_baselines_progress.log"
POLL_SECS = 180

JOB_SQL = """
SELECT job_name, state,
       TO_CHAR(last_start_date,'YYYY-MM-DD HH24:MI:SS') last_start,
       TO_CHAR(last_run_duration) dur
FROM all_scheduler_jobs
WHERE owner='CISADM' AND job_name LIKE 'JOB_BASELINE_STREAM_%_ONCE'
ORDER BY 1
"""

COUNT_SQL = """
SELECT 'FT' t, COUNT(*) c FROM cisadm.ft_rpt_curr
UNION ALL SELECT 'FT_GL', COUNT(*) FROM cisadm.ft_gl_distribution_rpt_curr
UNION ALL SELECT 'BSEG_BILLED', COUNT(*) FROM cisadm.bseg_billed_usage_rpt_curr
UNION ALL SELECT 'BSEG_SQ', COUNT(*) FROM cisadm.bseg_sq_usage_rpt_curr
UNION ALL SELECT 'D1_USAGE', COUNT(*) FROM cisadm.d1_usage_rpt_curr
UNION ALL SELECT 'D1_SCALAR', COUNT(*) FROM cisadm.d1_usage_scalar_dtl_rpt_curr
UNION ALL SELECT 'D1_MSRMT', COUNT(*) FROM cisadm.d1_msrmt_rpt_curr
UNION ALL SELECT 'CMS_SA', COUNT(*) FROM cisadm.cms_sa_snapshot
"""


def run_sql(sql: str) -> dict:
    proc = subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts/local/run_client_oracle_sql.py"),
            "--client",
            "odessa_dev",
            "--sql",
            sql,
            "--format",
            "json",
        ],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        check=False,
    )
    out = proc.stdout.strip()
    if proc.returncode != 0:
        raise RuntimeError(f"sql failed rc={proc.returncode}\n{proc.stderr}\n{out}")
    # Runner prints banners then JSON; find first '[' or '{'
    for i, ch in enumerate(out):
        if ch in "[{":
            return json.loads(out[i:])
    raise RuntimeError(f"no json in output:\n{out[:500]}")


def extract_rows(payload: dict | list) -> list[dict]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        if "rows" in payload:
            return payload["rows"]
        statements = payload.get("statements") or payload.get("results")
        if isinstance(statements, list) and statements:
            last = statements[-1]
            if isinstance(last, dict) and "rows" in last:
                return last["rows"]
            if isinstance(last, list):
                return last
    return []


def main() -> int:
    DONE.unlink(missing_ok=True)
    while True:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        try:
            jobs = extract_rows(run_sql(JOB_SQL))
            counts = extract_rows(run_sql(COUNT_SQL))
        except Exception as exc:  # noqa: BLE001
            line = f"==== {ts} ERROR {exc}\n"
            PROGRESS.open("a").write(line)
            print(line, flush=True)
            time.sleep(POLL_SECS)
            continue

        block = {
            "ts": ts,
            "jobs": jobs,
            "counts": counts,
        }
        line = json.dumps(block, default=str) + "\n"
        PROGRESS.open("a").write(line)
        print(line, flush=True)

        states = {str(r.get("STATE") or r.get("state") or "").upper() for r in jobs}
        names = {str(r.get("JOB_NAME") or r.get("job_name") or "") for r in jobs}
        if len(names) >= 3 and "RUNNING" not in states and states:
            DONE.write_text("done\n")
            print("ALL_STREAMS_DONE", flush=True)
            return 0
        time.sleep(POLL_SECS)


if __name__ == "__main__":
    raise SystemExit(main())
