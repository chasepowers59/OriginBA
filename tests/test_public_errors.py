"""What a person sees when the database fails, and what they must never see (2026-10-05).

Driver and network errors name hosts, IP addresses, connection strings and service names;
the production-readiness audit found them returned verbatim on nine routes, the SQL
workspace's "Query failed: {exc}" among them (every role reaches it) and the data-source
save path ("Connection test failed: {exc}", the old H1 leak back on a second path). A
connection failure now reads as the unreachable note with a reference; any other driver
message keeps its first line (a person writing SQL needs "column X does not exist") with
hosts, addresses and connection strings removed. A static rule keeps it that way.
"""
from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api import public_errors as pe  # noqa: E402


class Scrub(unittest.TestCase):
    def test_hosts_addresses_and_connection_strings_are_removed(self):
        cases = {
            "connection to server at \"10.13.4.91\", port 5432 failed": "10.13.4.91",
            "DPY-6005: cannot connect to database (CONNECTION_ID=abc). smartcity-db-test-v1-2.originsmartops.com:1521/PTESTDB_ELLENSBURG.testprivatesn.testvcn.oraclevcn.com": "originsmartops",
            "could not connect postgresql://chase:secret@db.internal:5432/originba_v2": "secret",
            "SMTP error from smtp.office365.com:587 (535 auth failed)": "office365",
            "listener refused host=192.168.1.20 port=1521": "192.168.1.20",
        }
        for raw, leak in cases.items():
            with self.subTest(raw=raw):
                self.assertNotIn(leak, pe.scrub(raw))

    def test_a_sql_error_keeps_its_meaning_and_only_its_first_line(self):
        out = pe.scrub('ORA-00904: "BILLED_AMT": invalid identifier\nHelp: https://docs.oracle.com/error-help/db/ora-00904/')
        self.assertEqual(out, 'ORA-00904: "BILLED_AMT": invalid identifier')
        self.assertEqual(pe.scrub('column "foo" does not exist'), 'column "foo" does not exist')


class PublicError(unittest.TestCase):
    def test_a_connection_failure_reads_as_unreachable_with_a_reference(self):
        out = pe.public_error("Query failed", Exception("DPY-6005: cannot connect to database. host 10.0.0.5"), reference="abc123def456")
        self.assertIn("cannot be reached right now", out)
        self.assertIn("abc123def456", out)
        self.assertNotIn("10.0.0.5", out)

    def test_any_other_failure_keeps_its_prefix_and_scrubbed_first_line(self):
        out = pe.public_error("Query failed", Exception('ORA-00942: table or view "X"."Y" does not exist\nmore'), reference="r1")
        self.assertEqual(out, 'Query failed: ORA-00942: table or view "X"."Y" does not exist (reference r1)')


def _broad_handlers_returning_raw_text(path: Path) -> list[str]:
    """`except Exception` blocks whose response (raise/return/dict) carries str(exc) or {exc}."""
    tree = ast.parse(path.read_text())
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler) or not node.name:
            continue
        caught = node.type
        names = [caught] if not isinstance(caught, ast.Tuple) else list(caught.elts)
        if not any(isinstance(n, ast.Name) and n.id in ("Exception", "BaseException") for n in names):
            continue
        for stmt in node.body:
            if not isinstance(stmt, (ast.Raise, ast.Return)) and not (
                    isinstance(stmt, ast.Assign) and any(isinstance(t, ast.Subscript) for t in stmt.targets)):
                continue
            seg = ast.get_source_segment(path.read_text(), stmt) or ""
            if f"str({node.name})" in seg or f"{{{node.name}}}" in seg:
                found.append(f"{path.relative_to(ROOT)}:{stmt.lineno}")
    return found


class NoRawDriverText(unittest.TestCase):
    def test_no_broad_handler_returns_raw_exception_text(self):
        offenders = []
        for path in sorted((ROOT / "api").rglob("*.py")):
            if path.name == "nlq_server.py":   # not deployed (audit item 6)
                continue
            offenders += _broad_handlers_returning_raw_text(path)
        self.assertEqual(offenders, [], "broad handlers returning raw exception text:\n  " + "\n  ".join(offenders))


if __name__ == "__main__":
    unittest.main()
