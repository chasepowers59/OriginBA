"""Every api module parses and imports.

Added after breaking one and watching the suite stay green. Patching
api/report_schedules.py left a function-local import unindented -- a syntax error in a
module the API cannot run without -- and all 298 tests still passed, because the tests
that touch that file READ IT AS TEXT rather than importing it. `python -c "import
api.report_schedules"` found it in a second.

Eight api modules were named in no test at all when this was written, including
api.report_schedule_runner -- the hourly cron entry point (`python -m
api.report_schedule_runner`). A syntax error there ships silently: the cron fails into
a log nobody reads, and no test says otherwise. Measured rather than assumed: with one
function-local import unindented in that module, the rest of the suite reported
**298 passed, 0 failed**, and these two tests named the module and the line.

WHAT THIS DOES NOT CATCH, stated so nobody trusts it further than it goes: a name that
is undefined INSIDE a function body. The same patch also left `date.fromisoformat`
behind while only `datetime` was imported, and neither compiling nor importing the
module reaches that line -- only calling it, or a linter's undefined-name check
(pyflakes F821). None of ruff, pyflakes or flake8 is in this project's dev
requirements, so that gap is a dependency decision rather than something to fake here.

Imports run in ONE subprocess: in-process imports would leave 52 modules' worth of
state in the shared interpreter, and this suite has already been bitten by
module-level env being read at import time.
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "api"


def api_modules() -> list[str]:
    out = []
    for path in sorted(API.rglob("*.py")):
        if path.name == "__init__.py":
            continue
        out.append(path.relative_to(ROOT).with_suffix("").as_posix().replace("/", "."))
    return out


class EveryModuleParsesTests(unittest.TestCase):
    """Syntax and indentation, without executing anything."""

    def test_all_api_modules_parse(self):
        broken = []
        for path in sorted(API.rglob("*.py")):
            try:
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except SyntaxError as exc:
                broken.append(f"{path.relative_to(ROOT)}:{exc.lineno}: {exc.msg}")
        self.assertEqual(broken, [], "modules failed to parse:\n" + "\n".join(broken))


class EveryModuleImportsTests(unittest.TestCase):
    def test_all_api_modules_import(self):
        mods = api_modules()
        self.assertGreater(len(mods), 40, "module discovery found suspiciously few files")
        script = (
            "import sys, importlib\n"
            "sys.path.insert(0, %r)\n"
            "bad = []\n"
            "for m in %r:\n"
            "    try:\n"
            "        importlib.import_module(m)\n"
            "    except Exception as exc:\n"
            "        bad.append(m + ': ' + type(exc).__name__ + ': ' + str(exc)[:120])\n"
            "print('\\n'.join(bad))\n"
        ) % (str(ROOT), mods)
        env = {
            **os.environ,
            # Import must not depend on a configured deployment: PORTAL_AUTH_SECRET is
            # only required when auth is enabled, and this test is about loadability.
            "PORTAL_AUTH_DISABLED": "true",
            "PORTAL_DEV_ORGANIZATION": "dev",
        }
        result = subprocess.run(
            [sys.executable, "-c", script], capture_output=True, text=True,
            timeout=180, cwd=str(ROOT), env=env,
        )
        self.assertEqual(result.returncode, 0, result.stderr[-800:])
        failures = [line for line in result.stdout.strip().splitlines() if line]
        self.assertEqual(failures, [], "modules failed to import:\n" + "\n".join(failures))


if __name__ == "__main__":
    unittest.main()
