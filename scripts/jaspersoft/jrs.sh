#!/bin/bash
# Run a scripts/jaspersoft tool with the JRS_* keys from ~/OriginBA-3/.env loaded.
#
# The tools resolve credentials as JRS_<ENV>_URL / _USER / _PASSWORD / _INSECURE; a plain shell
# has none of them, so `--env prod` fails on a missing key rather than on the server. This loads
# them for the child process only. VALUES ARE NEVER PRINTED -- the tools print key names only.
#
#   scripts/jaspersoft/jrs.sh jrs_repository.py --env prod whoami
#   scripts/jaspersoft/jrs.sh jrs_run_sweep.py --env test --org Ellensburg --out /tmp/x.json
#
# Lives in the repo (not a scratchpad) so a permission rule can name a stable path:
#   "Bash(scripts/jaspersoft/jrs.sh:*)" in .claude/settings.local.json
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
[ $# -ge 1 ] || { echo "usage: $(basename "$0") <tool.py> [args...]"; exit 2; }
[ -f "$REPO/.env" ] || { echo "no $REPO/.env; export the JRS_* keys yourself"; exit 2; }
tool="$1"; shift
cd "$REPO" && python3 - "$tool" "$@" <<'PY'
import os, sys, runpy, pathlib
for line in pathlib.Path(".env").read_text().splitlines():
    if line.startswith("JRS_") and "=" in line:
        key, value = line.split("=", 1)
        os.environ[key] = value.strip()
tool = sys.argv[1]; sys.argv = [tool] + sys.argv[2:]
runpy.run_path(f"scripts/jaspersoft/{tool}", run_name="__main__")
PY
