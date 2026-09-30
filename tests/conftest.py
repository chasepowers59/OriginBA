"""Suite-wide environment.

The tests ARE a development environment, so they declare it rather than the fences
being loosened to let them through. `auth_disabled()` and the verbose `/health` both
require affirmative proof of development (audit M3, M7) precisely because
`is_production()` defaults to False for an unrecognised deployment — the API runs on
Render, which sets none of the recognised markers, so "not production" proves nothing
there. Sixteen test modules set PORTAL_AUTH_DISABLED; this is the one place that says
which environment they are setting it in.

Individual tests still override ENVIRONMENT with mock.patch.dict to exercise the
production and undeclared paths.
"""

import os

os.environ.setdefault("ENVIRONMENT", "test")

# No test may reach a live Oracle database. 2026-09-29: a warmer-loop test stubbed the jobs it
# knew about, and the two added that day (Ori history, data quality) queried the real
# Ellensburg instance on every run, from a thread that outlived the test. Replacing the pool
# here (not per test) also covers such threads.
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api import demo_db  # noqa: E402


def _no_live_oracle(organization_id):
    raise RuntimeError(f"tests must not reach a live Oracle database ({organization_id})")


demo_db._oracle_pool = _no_live_oracle
