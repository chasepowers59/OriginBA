#!/usr/bin/env python3
"""Raw GET of a JasperReports Server REST path, printed in full (root login, or --org for a tenant).

    scripts/jaspersoft/jrs.sh jrs_get.py --env prod /rest_v2/jobs/9630798
    scripts/jaspersoft/jrs.sh jrs_get.py --env test --org Origin_DEV "/rest_v2/resources?folderUri=/SmartCity&recursive=false"

Password-like fields in a JSON body are masked before printing (only key names are ever shown).
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import jrs_run_sweep as sw  # noqa: E402


def masked(o):
    if isinstance(o, dict):
        return {k: ("***" if any(x in k.lower() for x in ("password", "passphrase", "secret")) else masked(v)) for k, v in o.items()}
    if isinstance(o, list):
        return [masked(x) for x in o]
    return o


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--env", required=True); ap.add_argument("--org"); ap.add_argument("path")
    ap.add_argument("--accept", default="application/json")
    a = ap.parse_args()
    os.environ["JRS_ENV"] = a.env; sw._AUTH.header = sw._auth_for(a.org) if a.org else None
    code, body, dt = sw._http(a.path, accept=a.accept, timeout=300)
    text = body.decode("utf-8", "replace")
    if a.accept == "application/json" and text.lstrip().startswith(("{", "[")):
        text = json.dumps(masked(json.loads(text)), indent=1)
    print(f"{code} in {dt:.1f}s\n{text}")
    return 0 if code == 200 else 1


if __name__ == "__main__":
    sys.exit(main())
