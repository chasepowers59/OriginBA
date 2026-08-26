#!/usr/bin/env python3
"""Reset a portal user's password — run BY THE ADMIN, locally, on the auth DB.

Account-recovery utility for the operator of this deployment. The new password is
NEVER passed on the command line (shell history) and never printed: it is read from
the PORTAL_NEW_PASSWORD environment variable, hashed with the app's own
pbkdf2_sha256 hasher, and written directly to the identity database. The user is
flagged must_change_password so the reset value is single-use.

    PORTAL_NEW_PASSWORD='<choose one>' python3 scripts/reset_portal_password.py admin@origin.local
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    email = sys.argv[1].strip().lower()
    new = os.environ.get("PORTAL_NEW_PASSWORD")
    if not new:
        print("Set PORTAL_NEW_PASSWORD in the environment (not on the command line).")
        return 2
    if len(new) < 10:
        print("Pick at least 10 characters.")
        return 2

    from api.auth.security import hash_password
    import sqlite3

    db_path = ROOT / "data" / "analytics_portal" / "portal_auth.db"
    conn = sqlite3.connect(db_path)
    cols = [r[1] for r in conn.execute("pragma table_info(portal_users)").fetchall()]
    pw_col = next((c for c in cols if "password" in c.lower() or "hash" in c.lower()), None)
    mcp_col = next((c for c in cols if "must_change" in c.lower()), None)
    if not pw_col:
        print("Could not find the password column; schema changed?")
        return 1
    hashed = hash_password(new)
    sets = f"{pw_col} = ?" + (f", {mcp_col} = 1" if mcp_col else "")
    cur = conn.execute(
        f"update portal_users set {sets} where lower(email) = ?", (hashed, email))
    conn.commit()
    if cur.rowcount == 0:
        print(f"No user with email {email}")
        return 1
    print(f"Password reset for {email}."
          + (" They must change it at next sign-in." if mcp_col else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
