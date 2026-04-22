# D1_USAGE_SCALAR_DTL_RPT_CURR Optimization Notes

## Current design traits that likely drive runtime

### 1. Full-history rebuild every day
The procedure still rebuilds all qualifying history on every daily run.

That means the daily job is not a delta load. It is a recurring full rebuild.

This is the most likely reason the job runtime is much higher than expected.

### 2. `DELETE` instead of `TRUNCATE`
This issue has been removed from the current workspace SQL.

The procedure now truncates the target before reload.

### 3. Repeated function-based timestamp filtering
The batch driver is:

```sql
NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm))
```

It is used:
- to find min and max month bounds
- to filter every monthly batch

If Oracle does not have a supporting function-based index, this can force repeated scans of `D1_USAGE`.

### 4. Customer resolution is not scoped to the current batch
`customer_choice` reads from `CI_ACCT_PER` and `CI_PER_NAME` without first limiting to accounts that are actually present in the current batch.

That means each monthly loop may reevaluate a customer-ranking set much larger than needed.

### 5. Lookup joins use `TRIM(...)` on both sides
Several joins to `CI_LOOKUP_VAL_L` use:

```sql
TRIM(field_name) = '...'
AND TRIM(field_value) = TRIM(source_value)
```

That can reduce index usefulness on the lookup table.

The lookup tables are usually small, so this is probably not the top runtime issue, but it is still avoidable overhead.

## Highest-value optimization candidates

### Option 1. Change from full rebuild to incremental refresh
Best long-term improvement if the business ever allows it.

Load only the recent change window instead of deleting and rebuilding all history every day.

This should be the first design option to evaluate if the business does not require full-history rebuilds on every run.

### Option 2. Replace `DELETE` with `TRUNCATE`
Implemented in the current workspace SQL.

### Option 3. Scope customer resolution to the current rebuild population
Implemented in the current workspace SQL.

`customer_choice` now ranks only the accounts that appear in the current rebuild population.

### Option 4. Remove the monthly loop
Implemented in the current workspace SQL.

The rebuild now uses one set-based insert instead of repeating the same normalized join graph month by month.

### Option 5. Stage or index the batch-driver timestamp
If the batch-driver expression is the main filter path, support it explicitly.

Typical options:
- a function-based index on `NVL(start_dttm, NVL(cre_dttm, status_upd_dttm))`
- a staged working set for the current batch
- a persisted driver column if governance allows it

### Option 6. Clean up lookup joins
Remove unnecessary `TRIM(...)` calls where source values are already normalized.

This is lower priority than the first four options.

## Comparison to D1_USAGE_RPT_CURR
`D1_USAGE_RPT_CURR` uses the same monthly full-rebuild pattern, but it runs much faster because:

- it drives one row per usage header instead of one row per scalar detail
- it does not join to `D1_USAGE_SCALAR_DTL`
- it does not carry as much lower-grain quantity detail

That makes the scalar-detail snapshot inherently heavier even before further optimizations.

## Recommended next steps
1. Recompile the procedure and run a full refresh in DEV or QA.
2. Run `04_validation_queries.sql`.
3. Run `05_intensive_qa_queries.sql`.
4. Capture total runtime after the single-pass rewrite.
5. If runtime is still too high, the next decision is incremental loading versus source-side physical design support.
