# FT_RPT_CURR Index Benchmark Checklist

## Goal
Decide whether a new index on `CISADM.FT_RPT_CURR` materially improves report retrieval for the actual FT report filter pattern.

This checklist assumes the common filters are:
- `ACCOUNTING_DT`
- `FT_TYPE_FLG`

## First principles
- Indexes are table-specific.
- Existing indexes on `CI_FT` or other source objects do not automatically help queries against `FT_RPT_CURR`.
- New snapshot-table indexes should be driven by the real `WHERE` clause, not just by columns that feel important.
- Prefer filtering on `FT_TYPE_FLG` rather than `FT_TYPE_FLG_DESC`.

## Recommended starting point
Start with:

```sql
CREATE INDEX CISADM.XOBA_FTRPT_FT_ACCTDT
    ON CISADM.FT_RPT_CURR (FT_TYPE_FLG, ACCOUNTING_DT);
```

Why:
- `FT_TYPE_FLG` is typically an equality filter.
- `ACCOUNTING_DT` is typically a range filter.
- For a composite B-tree index, putting the equality predicate first and the date range second is a sound first test.

## Secondary candidate
If many real FT reports use only accounting-date ranges and do not filter by FT type, test:

```sql
CREATE INDEX CISADM.XOBA_FTRPT_ACCTDT
    ON CISADM.FT_RPT_CURR (ACCOUNTING_DT);
```

This is broader but usually weaker than the composite index for the specific `FT_TYPE_FLG + ACCOUNTING_DT` pattern.

## Test order
1. Baseline with no new test index.
2. Test candidate 1: `(FT_TYPE_FLG, ACCOUNTING_DT)`.
3. Test candidate 2 only if many reports are date-only.

Do not keep stacking test indexes while benchmarking. Test one at a time.

## Before each test
1. Pick one real slow FT report slice.
2. Keep the same date window and FT type for every run.
3. Use the benchmark queries in `09_index_candidate_tests.sql`.
4. Record:
   - query name
   - filters used
   - returned row count
   - elapsed time
   - whether the query felt materially faster

## After creating a candidate index
1. Gather fresh stats in DEV if allowed:

```sql
BEGIN
    DBMS_STATS.GATHER_TABLE_STATS(
        ownname => 'CISADM',
        tabname => 'FT_RPT_CURR',
        cascade => TRUE
    );
END;
/
```

2. Re-run the same benchmark queries.
3. Compare elapsed time against the baseline.
4. Drop the test index if it does not materially help.

## What counts as a good result
Keep the index only if it clearly improves the real query pattern.

Good signals:
- the detail extract is materially faster
- the aggregate query is materially faster
- the improvement is consistent across repeated runs

Weak signals:
- only tiny improvement
- only a count query gets faster
- the improvement is inconsistent across repeated runs

## When not to expect much from an index
An index may not help much when:
- the date range is very wide
- the query returns a large share of the table anyway
- the report sorts a large result set after filtering

In those cases, Oracle may still correctly choose a full table scan.

## Suggested benchmark record template

| Test Run | Candidate Index | Filters | Rows Returned | Elapsed Time | Keep? | Notes |
|---|---|---|---:|---|---|---|
| Baseline | none | `ACCOUNTING_DT + FT_TYPE_FLG` |  |  |  |  |
| Candidate 1 | `FT_TYPE_FLG, ACCOUNTING_DT` | `ACCOUNTING_DT + FT_TYPE_FLG` |  |  |  |  |
| Candidate 2 | `ACCOUNTING_DT` | `ACCOUNTING_DT only` |  |  |  |  |

## Decision rule
- If `(FT_TYPE_FLG, ACCOUNTING_DT)` clearly helps the real FT report pattern, keep it.
- If most reports are truly date-only, test `ACCOUNTING_DT` separately rather than assuming one index solves both patterns.
- If neither helps enough, stop adding indexes and reassess the actual query shape and result volume.
