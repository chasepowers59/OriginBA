"""Letters from raw CISADM through a stubbed connection (synthetic rows only).

The contracts: the single-letter path runs the same SQL as the list with a one-row filter,
so a letter fetched alone EQUALS the same letter in the list; the balance is keyed by the
LETTER, never the account; a read past the row ceiling RAISES rather than truncating
(the generic execute_query stops at 5,000 rows in silence, and a month of Ellensburg
events is 23,157). Every letters SQL file loads through the reporting-scope fence.

The organization's engine picks the dialect: a Postgres org reads sql/postgres through its
warehouse, an Oracle org reads sql/oracle (CISADM-qualified) through its own connection. The
dialect changes the SQL and the driver, never the letter: the same rows through a fake
python-oracledb build letters EQUAL to the Postgres ones.
"""
from __future__ import annotations

import ast
import inspect
import re
import sys
import tempfile
import unittest
from contextlib import contextmanager
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.letters import repository, source  # noqa: E402
from api.letters.model import Kind  # noqa: E402
from api.oracle_client import oracledb  # noqa: E402
from api.sql_workspace_validator import SqlWorkspaceValidationError, strip_sql_noise  # noqa: E402

A1, A2 = "1000000001", "1000000002"


def _person(**over):
    row = {"address_source": "PER", "copies": 1, "name1": "Rivera,Alex", "name2": "", "name3": "",
           "p_address1": "100 Example Avenue", "p_address2": "Apt 4", "p_address3": None, "p_address4": None,
           "p_city": "Springfield", "p_state": "IL", "p_postal": "62701", "p_country": "USA",
           "m_address1": "200 Sample Road", "m_address2": None, "m_address3": None, "m_address4": None,
           "m_city": "Springfield", "m_state": "IL", "m_postal": "62702", "m_country": "USA",
           "person_id": "2000000001", "customer_name": "Rivera,Alex"}
    row.update(over)
    return row


def _contact(cc_id, when, contact_class, contact_type, template, account, **over):
    row = {"cc_id": cc_id, "cc_dttm": when, "contact_class": contact_class, "contact_type": contact_type,
           "contact_type_description": "", "template_code": template, "body": "", "letter_print_dttm": None,
           "account_id": account, **_person()}
    row.update(over)
    return row


def tables():
    return {
        "letters": [
            _contact("3000000001", datetime(2028, 3, 8, 6, 30), "C&C", "REG-REMINDER", "CIR-REG-REM", A1),
            _contact("3000000002", datetime(2028, 3, 20, 7, 0), "C&C", "DISCONNECTED", "CIR-SP-DISCN", A1,
                     address_source="PREM"),
            _contact("3000000003", datetime(2028, 3, 10, 9, 0), "C&C", "NSF", "CIR-NSF", A2),
            _contact("3000000004", datetime(2028, 3, 11, 9, 0), "C&C", "AUTOCALL", "CIR-AUTOCALL", A2),
            _contact("3000000005", datetime(2028, 3, 12, 9, 0), "GEN", "WELCOME", "CIR-WELCOME", A2),
        ],
        # the SAME account on two dates: two different balances
        "balances": [{"cc_id": "3000000001", "balance": Decimal("187.45")},
                     {"cc_id": "3000000002", "balance": Decimal("250.10")},
                     {"cc_id": "3000000003", "balance": Decimal("40.00")}],
        # ARS_AMT 0 on the header: the SA sum is the amount
        "collection_processes": [{"cc_id": "3000000001", "process_id": "P1", "template_code": "NORMAL-DEBT",
                                  "arrears_amount": Decimal("0"), "arrears_as_of": date(2028, 2, 27)}],
        "collection_services": [
            {"process_id": "P1", "sa_id": "5000000002", "service_type": "Gas Residential", "amount": Decimal("69.43"),
             "address1": "100 Example Avenue", "city": "Springfield", "state": "IL", "postal": "62701"},
            {"process_id": "P1", "sa_id": "5000000003", "service_type": "Water Residential", "amount": Decimal("63.26"),
             "address1": "100 Example Avenue", "city": "Springfield", "state": "IL", "postal": "62701"}],
        "collection_events": [
            {"process_id": "P1", "evt_seq": 10, "event_type_cd": "REMIND", "event_type": "Send reminder",
             "status_cd": "30", "trigger_dt": date(2028, 3, 8), "completion_dt": date(2028, 3, 8)},
            {"process_id": "P1", "evt_seq": 20, "event_type_cd": "AUTOCALL", "event_type": "Automated collections call",
             "status_cd": "10", "trigger_dt": date(2028, 3, 18), "completion_dt": None},
            {"process_id": "P9", "evt_seq": 10, "event_type_cd": "X", "event_type": "Another process",
             "status_cd": "10", "trigger_dt": date(2028, 3, 9), "completion_dt": None}],
        "severance_processes": [{"cc_id": "3000000002", "process_id": "S1", "template_code": "SEV-STD",
                                 "arrears_amount": Decimal("84.87"), "arrears_as_of": date(2028, 2, 27),
                                 "sa_id": "5000000003", "service_type": "Water Residential",
                                 "address1": "100 Example Avenue", "city": "Springfield", "state": "IL",
                                 "postal": "62701"}],
        "severance_events": [
            {"process_id": "S1", "evt_seq": 20, "event_type_cd": "CUT-NONPAY",
             "event_type": "Disconnect service for non-payment", "status_cd": "30",
             "trigger_dt": date(2028, 3, 18), "completion_dt": date(2028, 3, 18)},
            {"process_id": "S1", "evt_seq": 40, "event_type_cd": "EXPIRE-SA", "event_type": "Expire service agreement",
             "status_cd": "10", "trigger_dt": date(2028, 3, 30), "completion_dt": None}],
        "writeoff_processes": [], "writeoff_events": [], "writeoff_services": [],
        "returned_payments": [{"cc_id": "3000000003", "adjustment_id": "600000000001", "fee_amount": Decimal("20.00"),
                               "payment_date": date(2028, 3, 1), "payment_amount": Decimal("598.45"),
                               "tender_type": "Check"}],
        "late_fees": [{"adj_id": "600000000002", "amount": Decimal("10.88"), "charged_on": datetime(2028, 3, 9, 1, 0),
                       "sa_id": "5000000004", "account_id": A1, "service_type": "Electric Residential",
                       "sp_address1": "100 Example Avenue", "sp_city": "Springfield", "sp_state": "IL",
                       "sp_postal": "62701", **_person()}],
        "late_fee_balances": [{"adj_id": "600000000002", "balance": Decimal("198.33")}],
    }


class FakeCursor:
    """Answers each tagged letters query from `tables`, emulating the one-row filters."""

    def __init__(self, conn):
        self.conn, self.description, self._rows = conn, None, []

    def execute(self, sql, binds=None):
        self.conn.executed.append((sql, binds))
        tag = re.match(r"/\* letters:(\w+) \*/", sql)
        if not tag:
            self.description, self._rows = None, []
            return
        rows = self.conn.tables[tag.group(1)]
        for key in ("cc_id", "adj_id"):
            if binds and key in binds:
                rows = [r for r in rows if key not in r or r[key] == binds[key]]
        self._rows = [dict(r) for r in rows]
        self.description = [(k,) for k in (rows[0] if rows else {"none": None})]

    def fetchmany(self, size):
        out, self._rows = self._rows[:size], self._rows[size:]
        return [tuple(r.values()) for r in out]

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


class FakeConnection:
    def __init__(self, data):
        self.tables, self.executed, self.named = data, [], []

    def cursor(self, name=None):
        if name:
            self.named.append(name)
        return FakeCursor(self)


def fake(data=None, connection_class=None):
    conn = (connection_class or FakeConnection)(data if data is not None else tables())

    @contextmanager
    def connect(_org):
        yield conn
    return conn, connect


class FakeOracleCursor:
    """python-oracledb as the letters meet it: every `:name` in the statement must be bound and
    every bind used, column names come back UPPERCASE, a DATE comes back as a datetime, '' is NULL,
    a CHAR key is blank-padded, and NUMBER arrives as a float unless an output type handler asks
    for Decimal."""

    def __init__(self, conn):
        self.conn, self.description, self._rows = conn, None, []
        self.arraysize, self.prefetchrows, self.outputtypehandler = 100, 2, None

    def var(self, typ, arraysize=None):
        return ("var", typ)

    def _exact_numbers(self):
        meta = SimpleNamespace(type_code=oracledb.DB_TYPE_NUMBER, name="AMOUNT")
        return self.outputtypehandler is not None and self.outputtypehandler(self, meta) == ("var", Decimal)

    def _value(self, key, value, exact):
        if value == "":
            return None
        if isinstance(value, date) and not isinstance(value, datetime):
            return datetime.combine(value, time())
        if isinstance(value, Decimal) and not exact:
            return float(value)
        if key == "process_id":
            return value.ljust(10)
        return value

    def execute(self, sql, binds=None):
        binds = binds or {}
        self.conn.executed.append((sql, binds))
        tag = re.match(r"/\* letters:(\w+) \*/", sql)
        if not tag:
            self.description, self._rows = None, []
            return
        code = strip_sql_noise(sql)
        if re.search(r"%\(|\{\w+\}|\?", code):
            raise AssertionError(f"an unresolved placeholder reached Oracle: {tag.group(1)}")
        if set(re.findall(r":(\w+)", code)) != set(binds):
            raise AssertionError(f"ORA-01008/DPY-4008: markers and binds differ in {tag.group(1)}")
        rows = self.conn.tables[tag.group(1)]
        for key in ("cc_id", "adj_id"):
            if key in binds:
                rows = [r for r in rows if key not in r or r[key] == binds[key]]
        exact = self._exact_numbers()
        self._rows = [{k: self._value(k, v, exact) for k, v in r.items()} for r in rows]
        self.description = [(k.upper(),) for k in (rows[0] if rows else {"none": None})]

    def fetchmany(self, size):
        out, self._rows = self._rows[:size], self._rows[size:]
        return [tuple(r.values()) for r in out]

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


class FakeOracleConnection:
    def __init__(self, data):
        self.tables, self.executed, self.call_timeout, self.timeouts = data, [], 0, []

    def cursor(self):                   # python-oracledb names no cursors
        self.timeouts.append(self.call_timeout)
        return FakeOracleCursor(self)


def fake_oracle(data=None):
    return fake(data, FakeOracleConnection)


class RepositoryTests(unittest.TestCase):
    def setUp(self):
        self.conn, self.connect = fake()
        self.letters = repository.list_letters("demo25", date(2028, 3, 1), date(2028, 3, 31),
                                               connection=self.connect)
        self.by_id = {l.letter_id: l for l in self.letters}

    def test_the_list_holds_the_letters_and_late_fees_oldest_first(self):
        self.assertEqual([l.letter_id for l in self.letters],
                         ["CC-3000000001", "ADJ-600000000002", "CC-3000000003", "CC-3000000002"])
        self.assertNotIn("CC-3000000004", self.by_id, "an auto-dialer call is not a letter")
        self.assertNotIn("CC-3000000005", self.by_id, "a welcome letter outside a collections class is not one")

    def test_the_window_includes_its_last_day(self):
        binds = [b for sql, b in self.conn.executed if sql.startswith("/* letters:letters */")][0]
        self.assertEqual((binds["from_ts"], binds["to_ts"]), (datetime(2028, 3, 1), datetime(2028, 4, 1)))

    def test_the_process_behind_each_letter(self):
        reminder = self.by_id["CC-3000000001"]
        self.assertEqual(reminder.kind, Kind.REMINDER)
        self.assertEqual(reminder.debt.process_id, "P1")
        self.assertEqual(reminder.debt.arrears_amount, Decimal("132.69"), "header ARS_AMT 0: the SA sum")
        self.assertEqual((reminder.debt.next_action_on, reminder.debt.next_action_type),
                         (date(2028, 3, 18), "Automated collections call"))
        self.assertEqual(len(reminder.debt.services), 2)
        cut = self.by_id["CC-3000000002"]
        self.assertEqual(cut.kind, Kind.DISCONNECTED, "the letter follows a COMPLETED cut: not a warning")
        self.assertEqual(cut.debt.cut_completed_on, date(2028, 3, 18))
        self.assertEqual(cut.debt.next_action_on, date(2028, 3, 30))
        nsf = self.by_id["CC-3000000003"]
        self.assertEqual((nsf.returned_payment.fee_amount, nsf.returned_payment.payment_amount),
                         (Decimal("20.00"), Decimal("598.45")))
        fee = self.by_id["ADJ-600000000002"]
        self.assertEqual((fee.kind, fee.late_fee.amount), (Kind.LATE_FEE, Decimal("10.88")))

    def test_the_address_follows_c2m_s_address_source(self):
        self.assertEqual(self.by_id["CC-3000000001"].mailing_address.address1, "100 Example Avenue", "PER: the person")
        self.assertEqual(self.by_id["CC-3000000002"].mailing_address.address1, "200 Sample Road", "else the mailing premise")

    def test_the_balance_is_keyed_by_the_letter_not_the_account(self):
        first, second = self.by_id["CC-3000000001"], self.by_id["CC-3000000002"]
        self.assertEqual(first.account_id, second.account_id)
        self.assertEqual((first.account_balance, second.account_balance), (Decimal("187.45"), Decimal("250.10")))
        self.assertEqual(self.by_id["ADJ-600000000002"].account_balance, Decimal("198.33"))

    def test_a_single_letter_equals_the_same_letter_in_the_list(self):
        for letter_id, listed in self.by_id.items():
            with self.subTest(letter=letter_id):
                conn, connect = fake()
                alone = repository.get_letter("demo25", letter_id, connection=connect)
                self.assertEqual(alone, listed)
                one_row = [b for sql, b in conn.executed if sql.startswith("/* letters:")]
                self.assertTrue(one_row and all(("cc_id" in b) or ("adj_id" in b) for b in one_row),
                                "the single-letter path binds its id into every query")

    def test_an_unknown_or_malformed_id(self):
        _, connect = fake()
        self.assertIsNone(repository.get_letter("demo25", "CC-9999999999", connection=connect))
        with self.assertRaises(ValueError):
            repository.get_letter("demo25", "CC-1 or 1=1", connection=connect)


class SourceTests(unittest.TestCase):
    def test_the_dialect_follows_the_organization_s_engine(self):
        self.assertEqual(source.dialect_for("demo25"), "postgres")
        self.assertEqual(source.dialect_for("ellensburg"), "oracle")
        with mock.patch.object(source, "org_backend", return_value=("snowflake", "dbt")):
            with self.assertRaises(source.UnsupportedEngine):
                source.dialect_for("elsewhere")

    def test_the_row_ceiling_raises_rather_than_truncating(self):
        data = tables()
        data["collection_events"] = data["collection_events"] * 2      # 6 rows past a ceiling of 5
        _, connect = fake(data)
        with self.assertRaises(source.RowCeilingExceeded) as err:
            repository.list_letters("demo25", date(2028, 3, 1), date(2028, 3, 31), connection=connect, ceiling=5)
        self.assertIn("collection_events", str(err.exception))

    def test_the_reads_are_read_only_pinned_to_cisadm_and_streamed(self):
        conn, connect = fake()
        repository.list_letters("demo25", date(2028, 3, 1), date(2028, 3, 31), connection=connect)
        setup = " ".join(sql for sql, _ in conn.executed if not sql.startswith("/* letters:"))
        self.assertIn("READ ONLY", setup.upper())
        self.assertIn("search_path = cisadm", setup)
        self.assertIn("statement_timeout", setup)
        self.assertTrue(conn.named, "fetched through a server-side cursor, not loaded whole")

    def test_the_generic_query_path_is_never_used(self):
        for module in (source, repository):
            tree = ast.parse(inspect.getsource(module))
            names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
            names |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
            names |= {a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) for a in n.names}
            self.assertNotIn("execute_query", names, module.__name__)

    def _names(self, dialect):
        return sorted(p.stem for p in (source.SQL_ROOT / dialect).glob("*.sql"))

    def test_both_dialects_carry_the_same_queries(self):
        self.assertEqual(len(self._names("postgres")), 13, self._names("postgres"))
        self.assertEqual(self._names("oracle"), self._names("postgres"))

    def test_every_sql_file_passes_its_dialect_s_fence(self):
        for dialect in ("postgres", "oracle"):
            for name in self._names(dialect):
                with self.subTest(dialect=dialect, sql=name):
                    text = source.sql(name, dialect)    # raises when the fence refuses it
                    code = strip_sql_noise(text)
                    self.assertNotRegex(code, r"(?i)\b(insert|update|delete|merge|create|alter|drop)\b")
                    self.assertNotRegex(code, r"(?i)reporting", "letters read raw CISADM, never the canvases")
                    self.assertNotRegex(code, r"%|\?|(?<!:):\w", "no bind markers: values arrive through {filter} and {types}")
                    self.assertIn("{filter}", text)
                    self.assertEqual("{types}" in text, name.startswith("late_fee"))

    def test_postgres_names_are_unqualified_and_oracle_names_are_cisadm(self):
        for name in self._names("postgres"):
            with self.subTest(dialect="postgres", sql=name):
                self.assertNotRegex(source.sql(name, "postgres"), r"\b\w+\.ci_", "search_path pins cisadm")
        for name in self._names("oracle"):
            with self.subTest(dialect="oracle", sql=name):
                code = strip_sql_noise(source.sql(name, "oracle"))
                tables = re.findall(r"(?i)\b(?:from|join)\s+([\w.]+)", code)
                self.assertTrue(tables)
                for table in tables:
                    self.assertRegex(table, r"^CISADM\.ci_\w+$", "the session's own schema is not CISADM")
                self.assertNotIn("::", code, "a Postgres cast")

    def test_the_loader_refuses_sql_the_fence_refuses(self):
        cases = {"postgres": (("secret", "select t.micr_id from ci_pay_tndr t where {filter}"),
                              ("elsewhere", "select 1 from landing.ci_cc c where {filter}"),
                              ("write", "update ci_cc set letter_print_dttm = now() where {filter}")),
                 "oracle": (("secret", "select t.micr_id from CISADM.ci_pay_tndr t where {filter}"),
                            ("elsewhere", "select 1 from ORIGINBA_STAGING.ci_cc c where {filter}"),
                            ("dictionary", "select 1 from all_users c where {filter}"),
                            ("dblink", "select 1 from CISADM.ci_cc@prod c where {filter}"),
                            ("write", "update CISADM.ci_cc set letter_print_dttm = sysdate where {filter}"))}
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(source, "SQL_ROOT", Path(tmp)):
            for dialect, files in cases.items():
                (Path(tmp) / dialect).mkdir()
                for name, text in files:
                    (Path(tmp) / dialect / f"{name}.sql").write_text(text)
                    with self.subTest(dialect=dialect, sql=name), self.assertRaises(SqlWorkspaceValidationError):
                        source.sql(name, dialect)


class OracleRepositoryTests(unittest.TestCase):
    """The same synthetic rows, through a fake python-oracledb connection for an Oracle org."""

    ORG = "ellensburg"

    def setUp(self):
        self.conn, self.connect = fake_oracle()
        self.letters = repository.list_letters(self.ORG, date(2028, 3, 1), date(2028, 3, 31), connection=self.connect)

    def queries(self, conn=None):
        return [(sql, b) for sql, b in (conn or self.conn).executed if sql.startswith("/* letters:")]

    def test_the_oracle_list_equals_the_postgres_list(self):
        _, connect = fake()
        postgres = repository.list_letters("demo25", date(2028, 3, 1), date(2028, 3, 31), connection=connect)
        self.assertEqual(len(self.letters), 4)
        self.assertEqual(self.letters, postgres)
        fee = {l.letter_id: l for l in self.letters}["ADJ-600000000002"]
        self.assertIsInstance(fee.late_fee.amount, Decimal, "money is exact, never a float")

    def test_it_reads_the_oracle_sql_with_named_binds(self):
        for sql, binds in self.queries():
            with self.subTest(sql=sql.splitlines()[0]):
                self.assertIn("CISADM.", sql)
                self.assertIn(":from_ts", sql)
                self.assertNotIn("%(", sql)
                self.assertIsInstance(binds["from_ts"], datetime)
        self.assertEqual(len(self.queries()), 13)

    def test_the_late_fee_types_bind_one_marker_each(self):
        late = [(sql, b) for sql, b in self.queries() if sql.startswith("/* letters:late_fee")]
        self.assertEqual(len(late), 2)
        for sql, binds in late:
            self.assertIn("in (:types_0)", sql)
            self.assertEqual(binds["types_0"], "LPC")
            self.assertNotIn("types", binds)

    def test_a_single_letter_equals_the_same_letter_in_the_list(self):
        for listed in self.letters:
            with self.subTest(letter=listed.letter_id):
                conn, connect = fake_oracle()
                self.assertEqual(repository.get_letter(self.ORG, listed.letter_id, connection=connect), listed)
                self.assertTrue(all({"cc_id"} <= set(b) or {"adj_id"} <= set(b) for _, b in self.queries(conn)))

    def test_one_read_only_transaction_with_a_call_timeout_and_no_session_change(self):
        setup = [sql for sql, _ in self.conn.executed if not sql.startswith("/* letters:")]
        self.assertEqual(setup, ["SET TRANSACTION READ ONLY"], "one moment for every query, and no writes")
        self.assertEqual(set(self.conn.timeouts), {source.ORACLE_CALL_TIMEOUT_MS})
        self.assertEqual(self.conn.call_timeout, 0, "the pooled session gets its own timeout back")

    def test_the_row_ceiling_raises_rather_than_truncating(self):
        data = tables()
        data["collection_events"] = data["collection_events"] * 2
        _, connect = fake_oracle(data)
        with self.assertRaises(source.RowCeilingExceeded) as err:
            repository.list_letters(self.ORG, date(2028, 3, 1), date(2028, 3, 31), connection=connect, ceiling=5)
        self.assertIn("collection_events", str(err.exception))


if __name__ == "__main__":
    unittest.main()
