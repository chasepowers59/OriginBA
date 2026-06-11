-- 4a) Manual first run (use 02a for baseline, 02 for scheduled rolling refresh)
BEGIN
    cisadm.refresh_workflow_queue_rpt_curr;
END;
/

-- 4b) Snapshot population by source
SELECT
    queue_source,
    COUNT(*) AS row_count
FROM cisadm.workflow_queue_rpt_curr
GROUP BY queue_source
ORDER BY queue_source;

-- 4c) Duplicate key check (should return 0 rows)
SELECT
    queue_source,
    queue_natural_key,
    COUNT(*) AS row_count
FROM cisadm.workflow_queue_rpt_curr
GROUP BY
    queue_source,
    queue_natural_key
HAVING COUNT(*) > 1;

-- 4d) Source parity
SELECT COUNT(*) AS snapshot_todo_count
FROM cisadm.workflow_queue_rpt_curr
WHERE queue_source = 'TODO';

SELECT COUNT(*) AS source_todo_count
FROM cisadm.ci_td_entry;

SELECT COUNT(*) AS snapshot_batch_count
FROM cisadm.workflow_queue_rpt_curr
WHERE queue_source = 'BATCH';

SELECT COUNT(*) AS source_batch_count
FROM cisadm.ci_batch_inst;

-- 4e) Null key check
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN queue_source IS NULL OR queue_natural_key IS NULL THEN 1 ELSE 0 END) AS null_key_rows
FROM cisadm.workflow_queue_rpt_curr;

-- 4f) Description coverage
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN td_type_desc IS NULL AND td_type_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_td_type_desc,
    SUM(CASE WHEN entry_status_desc IS NULL AND entry_status_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_entry_status_desc,
    SUM(CASE WHEN batch_cd_desc IS NULL AND batch_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_batch_cd_desc,
    SUM(CASE WHEN batch_run_status_desc IS NULL AND batch_run_status IS NOT NULL THEN 1 ELSE 0 END) AS missing_batch_run_status_desc,
    SUM(CASE WHEN thread_status_desc IS NULL AND thread_status IS NOT NULL THEN 1 ELSE 0 END) AS missing_thread_status_desc
FROM cisadm.workflow_queue_rpt_curr;

-- 4g) Open to-do profile
SELECT
    entry_status_flg,
    entry_status_desc,
    COUNT(*) AS todo_count
FROM cisadm.workflow_queue_rpt_curr
WHERE queue_source = 'TODO'
GROUP BY
    entry_status_flg,
    entry_status_desc
ORDER BY
    todo_count DESC,
    entry_status_flg;

-- 4h) Batch run status profile
SELECT
    batch_run_status,
    batch_run_status_desc,
    COUNT(*) AS batch_thread_count
FROM cisadm.workflow_queue_rpt_curr
WHERE queue_source = 'BATCH'
GROUP BY
    batch_run_status,
    batch_run_status_desc
ORDER BY
    batch_thread_count DESC,
    batch_run_status;

-- 4i) Rolling-window retention sanity
SELECT COUNT(*) AS stale_completed_todos_still_present
FROM cisadm.workflow_queue_rpt_curr snap
WHERE snap.queue_source = 'TODO'
  AND snap.queue_anchor_dttm < ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -6)
  AND NVL(snap.entry_status_flg, 'C') <> 'O';

SELECT COUNT(*) AS stale_completed_batches_still_present
FROM cisadm.workflow_queue_rpt_curr snap
WHERE snap.queue_source = 'BATCH'
  AND snap.queue_anchor_dttm < ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -6)
  AND snap.batch_end_dttm IS NOT NULL;

-- 4j) Spot-check open to-do entries
SELECT *
FROM (
    SELECT *
    FROM cisadm.workflow_queue_rpt_curr
    WHERE queue_source = 'TODO'
      AND entry_status_flg = 'O'
    ORDER BY td_cre_dttm DESC
)
WHERE ROWNUM <= 10;

-- 4k) Spot-check active batch thread instances
SELECT *
FROM (
    SELECT *
    FROM cisadm.workflow_queue_rpt_curr
    WHERE queue_source = 'BATCH'
      AND batch_end_dttm IS NULL
    ORDER BY inst_start_dttm DESC
)
WHERE ROWNUM <= 10;
