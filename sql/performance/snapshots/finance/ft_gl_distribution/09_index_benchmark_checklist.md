# FT_GL_DISTRIBUTION_RPT_CURR Index Benchmark Checklist

## Goal
Decide whether a new index on `CISADM.FT_GL_DISTRIBUTION_RPT_CURR` materially improves report retrieval for the actual report filter pattern.

This checklist assumes the most common filters are:
- `ACCOUNTING_DT`
- `FT_TYPE_FLG`
- `DST_ID`

## First principles
- Indexes are table-specific.
- Existing indexes on `CI_FT`, `CI_FT_GL`, or other source objects do not automatically help queries against `FT_GL_DISTRIBUTION_RPT_CURR`.
- New snapshot-table indexes should be driven by the `WHERE` clause, not just by columns that "look important".
- Description columns such as `FT_TYPE_FLG_DESC` and `DST_DESC` are usually worse index keys than `FT_TYPE_FLG` and `DST_ID`.

## Recommended starting point
Start with:

```sql
CREATE INDEX CISADM.XOBA_FTGLRPT_FT_DST_ACCTDT
    ON CISADM.FT_GL_DISTRIBUTION_RPT_CURR (FT_TYPE_FLG, DST_ID, ACCOUNTING_DT);
```

Why:
- `FT_TYPE_FLG` and `DST_ID` are equality filters in many report patterns.
- `ACCOUNTING_DT` is usually a range filter.
- For a composite B-tree index, equality predicates first and the date range last is a sound first test.

## Test order
1. Baseline with no new test index.
2. Test candidate 1: `(FT_TYPE_FLG, DST_ID, ACCOUNTING_DT)`.
3. If many reports omit `FT_TYPE_FLG`, test candidate 2: `(DST_ID, ACCOUNTING_DT)`.
4. If many reports omit `DST_ID`, test candidate 3: `(FT_TYPE_FLG, ACCOUNTING_DT)`.

Do not create all three and leave them in place while benchmarking. Test one at a time.

## Before each test
1. Pick one real slow report slice.
2. Keep the same date window and the same filter values for every run.
3. Use the benchmark queries in `08_index_candidate_tests.sql`.
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
        tabname => 'FT_GL_DISTRIBUTION_RPT_CURR',
        cascade => TRUE
    );
END;
/
```

2. Re-run the same benchmark queries.
3. Compare elapsed time against the baseline.
4. Drop the test index if it does not materially help.

## What counts as a good result
Keep the index only if it clearly improves the real query pattern, not just a synthetic count query.

Good signals:
- the detail extract is materially faster
- the aggregate query is materially faster
- the improvement is consistent across repeated runs

Weak signals:
- only tiny improvement
- improvement only on count queries, not detail extracts
- improvement only for a rare edge case

## When not to expect much from an index
An index may not help much when:
- the report returns a very large share of the table
- the date range is very wide
- filters are weakly selective
- users sort and return large volumes anyway

In those cases, Oracle may still correctly choose a full table scan.

## Recommended filter discipline for reports
- Prefer filtering on `FT_TYPE_FLG` instead of `FT_TYPE_FLG_DESC`.
- Prefer filtering on `DST_ID` instead of `DST_DESC`.
- Display the descriptions in the report, but filter on the code columns whenever possible.

## Suggested benchmark record template

| Test Run | Candidate Index | Filters | Rows Returned | Elapsed Time | Keep? | Notes |
|---|---|---|---:|---|---|---|
| Baseline | none | `ACCOUNTING_DT + FT_TYPE_FLG + DST_ID` |  |  |  |  |
| Candidate 1 | `FT_TYPE_FLG, DST_ID, ACCOUNTING_DT` | `ACCOUNTING_DT + FT_TYPE_FLG + DST_ID` |  |  |  |  |
| Candidate 2 | `DST_ID, ACCOUNTING_DT` | `ACCOUNTING_DT + DST_ID` |  |  |  |  |
| Candidate 3 | `FT_TYPE_FLG, ACCOUNTING_DT` | `ACCOUNTING_DT + FT_TYPE_FLG` |  |  |  |  |

## Decision rule
- If one candidate clearly helps the real report pattern, keep that one.
- If two candidates help different common report shapes, keep both only if the read benefit justifies the extra refresh overhead.
- If none help enough, stop adding indexes and reassess the query shape, date window, or extraction strategy.
