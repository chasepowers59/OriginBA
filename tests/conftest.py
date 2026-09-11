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
