-- Purpose:
--   Read-only preflight checks for the legacy measurement domain before
--   standardizing it into the D1_MSRMT_RPT_CURR snapshot.
--
-- Goal:
--   Prove whether the legacy domain preserves one row per measurement or
--   whether its activity/SP/install/component joins duplicate or remove
--   measurement rows.

-- 1) Source baseline from processed measurements
SELECT COUNT(*) AS source_measurement_rows
FROM cisadm.d1_msrmt;

SELECT
    measr_comp_id,
    msrmt_dttm,
    COUNT(*) AS source_key_count
FROM cisadm.d1_msrmt
GROUP BY
    measr_comp_id,
    msrmt_dttm
HAVING COUNT(*) > 1;

-- 2) Legacy-domain row count using the original activity-centered join path
SELECT COUNT(*) AS legacy_domain_rows
FROM cisadm.d1_activity act
INNER JOIN cisadm.d1_activity_rel_obj aro
    ON aro.d1_activity_id = act.d1_activity_id
INNER JOIN cisadm.d1_sp sp
    ON sp.d1_sp_id = aro.pk_value1
   AND aro.maint_obj_cd = 'D1-SP'
INNER JOIN cisadm.d1_install_evt ie
    ON ie.d1_sp_id = sp.d1_sp_id
INNER JOIN cisadm.d1_measr_comp mc
    ON mc.device_config_id = ie.device_config_id
   AND ie.bo_status_cd IN ('ON', 'CONN-COMM')
INNER JOIN cisadm.d1_msrmt msrmt
    ON msrmt.measr_comp_id = mc.measr_comp_id
LEFT JOIN cisadm.d1_init_msrmt_data imd
    ON imd.init_msrmt_data_id = msrmt.orig_init_msrmt_id;

-- 3) Legacy-domain distinct measurement keys after all joins
SELECT COUNT(*) AS legacy_distinct_measurements
FROM (
    SELECT
        msrmt.measr_comp_id,
        msrmt.msrmt_dttm
    FROM cisadm.d1_activity act
    INNER JOIN cisadm.d1_activity_rel_obj aro
        ON aro.d1_activity_id = act.d1_activity_id
    INNER JOIN cisadm.d1_sp sp
        ON sp.d1_sp_id = aro.pk_value1
       AND aro.maint_obj_cd = 'D1-SP'
    INNER JOIN cisadm.d1_install_evt ie
        ON ie.d1_sp_id = sp.d1_sp_id
    INNER JOIN cisadm.d1_measr_comp mc
        ON mc.device_config_id = ie.device_config_id
       AND ie.bo_status_cd IN ('ON', 'CONN-COMM')
    INNER JOIN cisadm.d1_msrmt msrmt
        ON msrmt.measr_comp_id = mc.measr_comp_id
    LEFT JOIN cisadm.d1_init_msrmt_data imd
        ON imd.init_msrmt_data_id = msrmt.orig_init_msrmt_id
    GROUP BY
        msrmt.measr_comp_id,
        msrmt.msrmt_dttm
);

-- 4) Measurements dropped by the legacy domain join path
SELECT COUNT(*) AS source_measurements_missing_from_legacy_domain
FROM cisadm.d1_msrmt src
LEFT JOIN (
    SELECT
        msrmt.measr_comp_id,
        msrmt.msrmt_dttm
    FROM cisadm.d1_activity act
    INNER JOIN cisadm.d1_activity_rel_obj aro
        ON aro.d1_activity_id = act.d1_activity_id
    INNER JOIN cisadm.d1_sp sp
        ON sp.d1_sp_id = aro.pk_value1
       AND aro.maint_obj_cd = 'D1-SP'
    INNER JOIN cisadm.d1_install_evt ie
        ON ie.d1_sp_id = sp.d1_sp_id
    INNER JOIN cisadm.d1_measr_comp mc
        ON mc.device_config_id = ie.device_config_id
       AND ie.bo_status_cd IN ('ON', 'CONN-COMM')
    INNER JOIN cisadm.d1_msrmt msrmt
        ON msrmt.measr_comp_id = mc.measr_comp_id
    LEFT JOIN cisadm.d1_init_msrmt_data imd
        ON imd.init_msrmt_data_id = msrmt.orig_init_msrmt_id
    GROUP BY
        msrmt.measr_comp_id,
        msrmt.msrmt_dttm
) legacy
    ON legacy.measr_comp_id = src.measr_comp_id
   AND legacy.msrmt_dttm = src.msrmt_dttm
WHERE legacy.measr_comp_id IS NULL;

-- 5) Duplicate inflation created by the legacy domain join path
SELECT NVL(SUM(dup.row_count - 1), 0) AS legacy_duplicate_excess_rows
FROM (
    SELECT
        msrmt.measr_comp_id,
        msrmt.msrmt_dttm,
        COUNT(*) AS row_count
    FROM cisadm.d1_activity act
    INNER JOIN cisadm.d1_activity_rel_obj aro
        ON aro.d1_activity_id = act.d1_activity_id
    INNER JOIN cisadm.d1_sp sp
        ON sp.d1_sp_id = aro.pk_value1
       AND aro.maint_obj_cd = 'D1-SP'
    INNER JOIN cisadm.d1_install_evt ie
        ON ie.d1_sp_id = sp.d1_sp_id
    INNER JOIN cisadm.d1_measr_comp mc
        ON mc.device_config_id = ie.device_config_id
       AND ie.bo_status_cd IN ('ON', 'CONN-COMM')
    INNER JOIN cisadm.d1_msrmt msrmt
        ON msrmt.measr_comp_id = mc.measr_comp_id
    LEFT JOIN cisadm.d1_init_msrmt_data imd
        ON imd.init_msrmt_data_id = msrmt.orig_init_msrmt_id
    GROUP BY
        msrmt.measr_comp_id,
        msrmt.msrmt_dttm
    HAVING COUNT(*) > 1
) dup;

-- 6) Sample duplicated measurement keys from the legacy domain
SELECT *
FROM (
    SELECT
        msrmt.measr_comp_id,
        msrmt.msrmt_dttm,
        COUNT(*) AS row_count
    FROM cisadm.d1_activity act
    INNER JOIN cisadm.d1_activity_rel_obj aro
        ON aro.d1_activity_id = act.d1_activity_id
    INNER JOIN cisadm.d1_sp sp
        ON sp.d1_sp_id = aro.pk_value1
       AND aro.maint_obj_cd = 'D1-SP'
    INNER JOIN cisadm.d1_install_evt ie
        ON ie.d1_sp_id = sp.d1_sp_id
    INNER JOIN cisadm.d1_measr_comp mc
        ON mc.device_config_id = ie.device_config_id
       AND ie.bo_status_cd IN ('ON', 'CONN-COMM')
    INNER JOIN cisadm.d1_msrmt msrmt
        ON msrmt.measr_comp_id = mc.measr_comp_id
    LEFT JOIN cisadm.d1_init_msrmt_data imd
        ON imd.init_msrmt_data_id = msrmt.orig_init_msrmt_id
    GROUP BY
        msrmt.measr_comp_id,
        msrmt.msrmt_dttm
    HAVING COUNT(*) > 1
    ORDER BY COUNT(*) DESC, msrmt.measr_comp_id, msrmt.msrmt_dttm
)
WHERE ROWNUM <= 50;

-- 7) Coverage of the proposed measurement-grain join design
SELECT
    COUNT(*) AS total_measurements,
    SUM(CASE WHEN mc.measr_comp_id IS NULL THEN 1 ELSE 0 END) AS missing_measr_comp,
    SUM(CASE WHEN src.orig_init_msrmt_id IS NOT NULL AND imd.init_msrmt_data_id IS NULL THEN 1 ELSE 0 END) AS missing_imd,
    SUM(CASE WHEN ie.install_evt_id IS NULL THEN 1 ELSE 0 END) AS missing_time_valid_install_evt,
    SUM(CASE WHEN ie.install_evt_id IS NOT NULL AND sp.d1_sp_id IS NULL THEN 1 ELSE 0 END) AS missing_sp_from_install_evt
FROM cisadm.d1_msrmt src
LEFT JOIN cisadm.d1_measr_comp mc
    ON mc.measr_comp_id = src.measr_comp_id
LEFT JOIN cisadm.d1_init_msrmt_data imd
    ON imd.init_msrmt_data_id = src.orig_init_msrmt_id
LEFT JOIN cisadm.d1_install_evt ie
    ON ie.device_config_id = mc.device_config_id
   AND (ie.d1_install_dttm IS NULL OR ie.d1_install_dttm <= src.msrmt_dttm)
   AND (ie.d1_removal_dttm IS NULL OR ie.d1_removal_dttm > src.msrmt_dttm)
   AND NOT EXISTS (
        SELECT 1
        FROM cisadm.d1_install_evt ie2
        WHERE ie2.device_config_id = ie.device_config_id
          AND (ie2.d1_install_dttm IS NULL OR ie2.d1_install_dttm <= src.msrmt_dttm)
          AND (ie2.d1_removal_dttm IS NULL OR ie2.d1_removal_dttm > src.msrmt_dttm)
          AND (
                NVL(ie2.d1_install_dttm, TIMESTAMP '1900-01-01 00:00:00') > NVL(ie.d1_install_dttm, TIMESTAMP '1900-01-01 00:00:00')
             OR (
                    NVL(ie2.d1_install_dttm, TIMESTAMP '1900-01-01 00:00:00') = NVL(ie.d1_install_dttm, TIMESTAMP '1900-01-01 00:00:00')
                AND ie2.install_evt_id > ie.install_evt_id
                )
              )
    )
LEFT JOIN cisadm.d1_sp sp
    ON sp.d1_sp_id = ie.d1_sp_id;

-- 8) Lookup-coverage check for the proposed measurement snapshot logic
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN msrmt_stat.descr IS NULL THEN 1 ELSE 0 END) AS missing_msrmt_status_desc,
    SUM(CASE WHEN msrmt_cond.descr IS NULL AND src.msrmt_cond_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_msrmt_cond_desc,
    SUM(CASE WHEN msrmt_use.descr IS NULL AND src.msrmt_use_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_msrmt_use_desc,
    SUM(CASE WHEN mc_type.descr100 IS NULL AND mc.measr_comp_type_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_mc_type_desc,
    SUM(CASE WHEN sp_type.descr100 IS NULL AND sp.d1_sp_type_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_sp_type_desc,
    SUM(CASE WHEN imd_data_src.descr IS NULL AND imd.data_src_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_imd_data_src_desc
FROM cisadm.d1_msrmt src
LEFT JOIN cisadm.d1_measr_comp mc
    ON mc.measr_comp_id = src.measr_comp_id
LEFT JOIN cisadm.d1_init_msrmt_data imd
    ON imd.init_msrmt_data_id = src.orig_init_msrmt_id
LEFT JOIN cisadm.d1_install_evt ie
    ON ie.device_config_id = mc.device_config_id
   AND (ie.d1_install_dttm IS NULL OR ie.d1_install_dttm <= src.msrmt_dttm)
   AND (ie.d1_removal_dttm IS NULL OR ie.d1_removal_dttm > src.msrmt_dttm)
   AND NOT EXISTS (
        SELECT 1
        FROM cisadm.d1_install_evt ie2
        WHERE ie2.device_config_id = ie.device_config_id
          AND (ie2.d1_install_dttm IS NULL OR ie2.d1_install_dttm <= src.msrmt_dttm)
          AND (ie2.d1_removal_dttm IS NULL OR ie2.d1_removal_dttm > src.msrmt_dttm)
          AND (
                NVL(ie2.d1_install_dttm, TIMESTAMP '1900-01-01 00:00:00') > NVL(ie.d1_install_dttm, TIMESTAMP '1900-01-01 00:00:00')
             OR (
                    NVL(ie2.d1_install_dttm, TIMESTAMP '1900-01-01 00:00:00') = NVL(ie.d1_install_dttm, TIMESTAMP '1900-01-01 00:00:00')
                AND ie2.install_evt_id > ie.install_evt_id
                )
              )
    )
LEFT JOIN cisadm.d1_sp sp
    ON sp.d1_sp_id = ie.d1_sp_id
LEFT JOIN cisadm.f1_bus_obj_status_l msrmt_stat
    ON msrmt_stat.bus_obj_cd = src.bus_obj_cd
   AND msrmt_stat.bo_status_cd = src.bo_status_cd
   AND msrmt_stat.language_cd = 'ENG'
LEFT JOIN cisadm.f1_ext_lookup_val_l msrmt_cond
    ON msrmt_cond.bus_obj_cd = 'D1-MeasurementConditionLookup'
   AND msrmt_cond.f1_ext_lookup_value = src.msrmt_cond_flg
   AND msrmt_cond.language_cd = 'ENG'
LEFT JOIN cisadm.ci_lookup_val_l msrmt_use
    ON msrmt_use.field_name = 'MSRMT_USE_FLG'
   AND msrmt_use.field_value = src.msrmt_use_flg
   AND msrmt_use.language_cd = 'ENG'
LEFT JOIN cisadm.d1_measr_comp_type_l mc_type
    ON mc_type.measr_comp_type_cd = mc.measr_comp_type_cd
   AND mc_type.language_cd = 'ENG'
LEFT JOIN cisadm.d1_sp_type_l sp_type
    ON sp_type.d1_sp_type_cd = sp.d1_sp_type_cd
   AND sp_type.language_cd = 'ENG'
LEFT JOIN cisadm.ci_lookup_val_l imd_data_src
    ON imd_data_src.field_name = 'DATA_SRC_FLG'
   AND imd_data_src.field_value = imd.data_src_flg
   AND imd_data_src.language_cd = 'ENG';
