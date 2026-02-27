# Jaspersoft Derived Table Rules

## Parser-Safe SQL Requirements
- Query must start with `SELECT`.
- No trailing semicolon.
- Keep syntax simple for domain parser stability.
- Prefer no bind syntax in Domain derived table SQL unless confirmed supported in target setup.

## Reliable Shape
Use:
```sql
SELECT ...
FROM (
  SELECT ...
) X
```

## Common Failures
- `The query is not valid. A derived table query must start with SELECT...`
  - Cause: SQL starts with `WITH` or comments.
  - Fix: wrap CTE logic in outer `SELECT * FROM (...)`.

- `ORA-00911: invalid character`
  - Cause: unsupported tokens in Domain parser path (`$P{}`, `:BIND`, stray semicolon).
  - Fix: use parser-safe static SQL and apply filtering in report/ad hoc layer.

- `String index out of range: -1`
  - Cause: Domain parser bug with certain SQL constructs.
  - Fix: simplify SQL, reduce nested complexity, ensure plain SELECT wrappers.

## Filter Strategy
When parameters are parser-problematic, expose filter fields in dataset:
- `BILL_CYCLE_CODE`
- `EVENT_DATE`
- `MOST_RECENT_BILL_CYCLE_SW`
- `IS_ERROR_SW`

Then apply filtering via Jasper input controls/ad hoc filters.

## Deployment Consistency
- Datasource aliases only:
  - `ORIGIN_DEV_DS`
  - `C2M_QA_DS`
  - `C2M_PROD_DS`
