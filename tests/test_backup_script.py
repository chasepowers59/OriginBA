"""Portal-state backup script: tests written before the code.

Contract (deploy/backup_portal_state.sh):
  - refuses to run without PORTAL_AUTH_DATABASE_URL, with a helpful message;
  - calls pg_dump against that URL with the portal tables/schema and writes a
    timestamped .sql.gz into the target directory (first argument, default
    ./backups) — verified with a fake pg_dump on PATH, no real database;
  - never prints the connection string (the password lives inside it).
"""
from __future__ import annotations

import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "deploy" / "backup_portal_state.sh"


class BackupScriptTests(unittest.TestCase):
    def test_script_exists_and_parses(self):
        self.assertTrue(SCRIPT.exists(), "deploy/backup_portal_state.sh missing")
        subprocess.run(["bash", "-n", str(SCRIPT)], check=True)

    def test_refuses_without_database_url(self):
        env = {k: v for k, v in os.environ.items() if k != "PORTAL_AUTH_DATABASE_URL"}
        r = subprocess.run(["bash", str(SCRIPT)], env=env,
                           capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("PORTAL_AUTH_DATABASE_URL", r.stdout + r.stderr)

    def test_invokes_pg_dump_and_writes_gz(self):
        with tempfile.TemporaryDirectory() as tmp:
            bindir = Path(tmp) / "bin"
            bindir.mkdir()
            fake = bindir / "pg_dump"
            # a fake pg_dump that records its args and emits dump content
            fake.write_text("#!/bin/bash\necho \"$@\" > \"$FAKE_LOG\"\necho '-- dump'\n")
            fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
            outdir = Path(tmp) / "out"
            log = Path(tmp) / "args.log"
            env = dict(os.environ)
            env["PATH"] = f"{bindir}:{env['PATH']}"
            env["PORTAL_AUTH_DATABASE_URL"] = "postgresql://u:SECRETPW@host:6543/postgres"
            env["FAKE_LOG"] = str(log)
            r = subprocess.run(["bash", str(SCRIPT), str(outdir)], env=env,
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            args = log.read_text()
            self.assertIn("portal_state", args)      # the state schema is in the dump
            dumps = list(outdir.glob("portal_state_*.sql.gz"))
            self.assertEqual(len(dumps), 1)
            # the secret never reaches the console
            self.assertNotIn("SECRETPW", r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
