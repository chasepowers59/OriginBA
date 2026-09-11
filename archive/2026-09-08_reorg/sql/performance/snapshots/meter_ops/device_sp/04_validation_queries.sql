-- 4a) Manual first run (use 02a for initial full-history load)
BEGIN
    cisadm.refresh_device_sp_rpt_curr;
END;
/

-- 4b) Row count parity (snapshot vs. source)
SELECT COUNT(*) AS snapshot_count
FROM cisadm.device_sp_rpt_curr;

SELECT COUNT(*) AS source_count
FROM cisadm.d1_dvc;

-- 4c) Duplicate key check (should return 0 rows)
SELECT
    d1_dvc_id,
    COUNT(*) AS row_count
FROM cisadm.device_sp_rpt_curr
GROUP BY d1_dvc_id
HAVING COUNT(*) > 1;

-- 4d) Null key check
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN d1_dvc_id IS NULL THEN 1 ELSE 0 END) AS null_d1_dvc_id_rows
FROM cisadm.device_sp_rpt_curr;

-- 4e) Description coverage check
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN device_type_desc IS NULL AND device_type_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_device_type_desc,
    SUM(CASE WHEN bo_status_desc IS NULL AND bo_status_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_bo_status_desc,
    SUM(CASE WHEN manufacturer_desc IS NULL AND manufacturer_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_manufacturer_desc,
    SUM(CASE WHEN model_desc IS NULL AND d1_model_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_model_desc,
    SUM(CASE WHEN asset_type_desc IS NULL AND asset_type_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_asset_type_desc,
    SUM(CASE WHEN sp_bo_status_desc IS NULL AND sp_bo_status_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_sp_bo_status_desc,
    SUM(CASE WHEN us_bo_status_desc IS NULL AND us_bo_status_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_us_bo_status_desc
FROM cisadm.device_sp_rpt_curr;

-- 4f) Install-event aggregate reconciliation
WITH install_src AS (
    SELECT
        cfg.d1_device_id,
        COUNT(DISTINCT ie.install_evt_id) AS install_event_count
    FROM cisadm.d1_dvc_cfg cfg
    JOIN cisadm.d1_install_evt ie
        ON ie.device_config_id = cfg.device_config_id
    GROUP BY cfg.d1_device_id
)
SELECT
    COUNT(*) AS mismatched_install_count_devices
FROM cisadm.device_sp_rpt_curr snap
JOIN install_src src
    ON src.d1_device_id = snap.d1_dvc_id
WHERE NVL(snap.install_event_count, 0) <> NVL(src.install_event_count, 0);

-- 4g) Configuration aggregate reconciliation
WITH cfg_src AS (
    SELECT
        cfg.d1_device_id,
        COUNT(*) AS device_config_count
    FROM cisadm.d1_dvc_cfg cfg
    GROUP BY cfg.d1_device_id
)
SELECT
    COUNT(*) AS mismatched_config_count_devices
FROM cisadm.device_sp_rpt_curr snap
JOIN cfg_src src
    ON src.d1_device_id = snap.d1_dvc_id
WHERE NVL(snap.device_config_count, 0) <> NVL(src.device_config_count, 0);

-- 4h) Currently installed flag sanity
SELECT
    currently_installed_sw,
    COUNT(*) AS device_count
FROM cisadm.device_sp_rpt_curr
GROUP BY currently_installed_sw
ORDER BY device_count DESC;

SELECT COUNT(*) AS installed_flag_without_sp
FROM cisadm.device_sp_rpt_curr
WHERE currently_installed_sw = 'Y'
  AND d1_sp_id IS NULL;

-- 4i) Asset linkage coverage
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN asset_id IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_asset_id,
    SUM(CASE WHEN asset_id IS NOT NULL AND asset_type_cd IS NULL THEN 1 ELSE 0 END) AS asset_id_without_asset_header
FROM cisadm.device_sp_rpt_curr;

-- 4j) Device type distribution
SELECT
    device_type_cd,
    device_type_desc,
    COUNT(*) AS device_count,
    SUM(CASE WHEN currently_installed_sw = 'Y' THEN 1 ELSE 0 END) AS installed_count
FROM cisadm.device_sp_rpt_curr
GROUP BY
    device_type_cd,
    device_type_desc
ORDER BY
    device_count DESC,
    device_type_cd;

-- 4k) Spot-check currently installed devices
SELECT *
FROM (
    SELECT *
    FROM cisadm.device_sp_rpt_curr
    WHERE currently_installed_sw = 'Y'
    ORDER BY dvc_status_upd_dttm DESC NULLS LAST, d1_dvc_id
)
WHERE ROWNUM <= 10;

-- 4l) Rolling-window retention sanity (dormant devices older than 6 months, not installed)
SELECT COUNT(*) AS stale_devices_still_present
FROM cisadm.device_sp_rpt_curr snap
WHERE snap.dvc_status_upd_dttm < ADD_MONTHS(TRUNC(SYSDATE), -6)
  AND NVL(snap.currently_installed_sw, 'N') = 'N'
  AND NOT EXISTS (
      SELECT 1
      FROM cisadm.d1_dvc_cfg cfg
      JOIN cisadm.d1_install_evt ie
          ON ie.device_config_id = cfg.device_config_id
      WHERE cfg.d1_device_id = snap.d1_dvc_id
        AND (
            ie.d1_install_dttm >= ADD_MONTHS(TRUNC(SYSDATE), -6)
            OR ie.d1_removal_dttm >= ADD_MONTHS(TRUNC(SYSDATE), -6)
            OR ie.status_upd_dttm >= ADD_MONTHS(TRUNC(SYSDATE), -6)
        )
  )
  AND NOT EXISTS (
      SELECT 1
      FROM cisadm.d1_dvc_cfg cfg
      WHERE cfg.d1_device_id = snap.d1_dvc_id
        AND (
            cfg.eff_dttm >= ADD_MONTHS(TRUNC(SYSDATE), -6)
            OR cfg.status_upd_dttm >= ADD_MONTHS(TRUNC(SYSDATE), -6)
        )
  );
