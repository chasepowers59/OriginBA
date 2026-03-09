# Database Read-Only Non-Negotiables

## Policy
All discovery, diagnostics, validation, and performance testing in this repository must be read-only.

## Allowed Operations
- `SELECT` statements
- read-only metadata queries (`ALL_TAB_COLUMNS`, `ALL_COL_COMMENTS`, `ALL_TAB_COMMENTS`, etc.)
- read-only assertions that fail via arithmetic/error checks

## Forbidden Operations
- DML: `INSERT`, `UPDATE`, `DELETE`, `MERGE`
- DDL: `CREATE`, `ALTER`, `DROP`, `TRUNCATE`, `RENAME`
- admin/statistics operations: `DBMS_STATS`, grants/revokes
- transaction-changing actions used to mutate state

## Enforcement
- CI gate: `.github/workflows/sql-quality.yml`
- Read-only scanner: `scripts/repo/sql_read_only_guard.py`
- Validation preflight: `sql/performance/billed_usage/validation/00_read_only_preflight.sql`
- Dictionary discovery pack: `sql/diagnostics/cisadm_dictionary/`

## Credential Handling
- Automation runner uses explicit `ConnectString` parameter.
- `.env` is not auto-loaded by validation scripts.
- Use least-privilege read-only DB users only.
