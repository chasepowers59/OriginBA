CREATE OR REPLACE PROCEDURE cisadm.refresh_workflow_queue_rpt_curr AS
    v_load_dttm TIMESTAMP := SYSTIMESTAMP;
BEGIN
    EXECUTE IMMEDIATE 'TRUNCATE TABLE cisadm.workflow_queue_rpt_curr';

    INSERT INTO cisadm.workflow_queue_rpt_curr (
        queue_source,
        queue_natural_key,
        queue_anchor_dttm,
        td_entry_id,
        td_type_cd,
        td_type_desc,
        entry_status_flg,
        entry_status_desc,
        td_priority_flg,
        td_priority_desc,
        role_id,
        role_desc,
        assigned_to,
        assigned_to_name,
        assigned_user_id,
        assigned_user_name,
        complete_user_id,
        complete_user_name,
        td_cre_dttm,
        assigned_dttm,
        complete_dttm,
        td_batch_cd,
        td_batch_nbr,
        message_cat_nbr,
        message_nbr,
        message_text,
        td_comments,
        days_old,
        assigned_tm_days,
        assigned_tm_mins,
        complete_tm_days,
        complete_tm_mins,
        unassigned_tm_days,
        unassigned_tm_mins,
        fk_acct_id,
        fk_sa_id,
        fk_prem_id,
        fk_per_id,
        fk_d1_sp_id,
        fk_us_id,
        fk_asset_id,
        fk_d1_device_id,
        fk_measr_comp_id,
        fk_contact_id,
        person_name_upr,
        prem_address1,
        prem_address1_upr,
        prem_city,
        prem_state,
        prem_postal,
        prem_type_cd,
        prem_type_desc,
        trend_area_cd,
        trend_area_desc,
        time_zone_cd,
        time_zone_desc,
        postal_5,
        scheduler_id,
        batch_cd,
        batch_cd_desc,
        batch_nbr,
        batch_rerun_nbr,
        batch_thread_nbr,
        batch_bus_dt,
        batch_start_dttm,
        batch_end_dttm,
        batch_run_status,
        batch_run_status_desc,
        batch_do_not_restart_sw,
        thread_status,
        thread_status_desc,
        thread_log_file_name,
        thread_retry_cnt,
        rec_proc_cnt,
        rec_err_cnt,
        inst_start_dttm,
        inst_end_dttm,
        inst_file_details,
        duration_hours,
        duration_mins,
        load_dttm
    )
    WITH
    todo_fk_pivot AS (
        SELECT
            td.td_entry_id,
            MAX(CASE WHEN ty.fld_name = 'ACCT_ID' THEN drl.key_value END) AS acct_id,
            MAX(CASE WHEN ty.fld_name = 'SA_ID' THEN drl.key_value END) AS sa_id,
            MAX(CASE WHEN ty.fld_name = 'PREM_ID' THEN drl.key_value END) AS prem_id,
            MAX(CASE WHEN ty.fld_name = 'PER_ID' THEN drl.key_value END) AS per_id,
            MAX(CASE WHEN ty.fld_name = 'D1_SP_ID' THEN drl.key_value END) AS d1_sp_id,
            MAX(CASE WHEN ty.fld_name = 'US_ID' THEN drl.key_value END) AS us_id,
            MAX(CASE WHEN ty.fld_name = 'ASSET_ID' THEN drl.key_value END) AS asset_id,
            MAX(CASE WHEN ty.fld_name = 'D1_DEVICE_ID' THEN drl.key_value END) AS d1_device_id,
            MAX(CASE WHEN ty.fld_name = 'MEASR_COMP_ID' THEN drl.key_value END) AS measr_comp_id,
            MAX(CASE WHEN ty.fld_name = 'CONTACT_ID' THEN drl.key_value END) AS contact_id,
            MAX(CASE WHEN ty.fld_name = 'CASE_ID' THEN drl.key_value END) AS case_id,
            MAX(CASE WHEN ty.fld_name = 'SP_ID' THEN drl.key_value END) AS sp_id
        FROM cisadm.ci_td_entry td
        LEFT JOIN cisadm.ci_td_drlkey drl
            ON drl.td_entry_id = td.td_entry_id
        LEFT JOIN cisadm.ci_td_drlkey_ty ty
            ON ty.td_type_cd = td.td_type_cd
           AND ty.seq_num = drl.seq_num
        GROUP BY td.td_entry_id
    ),
    todo_fk_ranked AS (
        SELECT
            p.td_entry_id,
            COALESCE(p.acct_id, x1.acct_id) AS acct_id,
            COALESCE(p.sa_id, x1.sa_id) AS sa_id,
            COALESCE(p.prem_id, cs.prem_id, sp.prem_id, x1.prem_id) AS prem_id,
            COALESCE(p.per_id, x1.per_id) AS per_id,
            COALESCE(p.d1_sp_id, x1.d1_sp_id) AS d1_sp_id,
            COALESCE(p.us_id, x1.us_id) AS us_id,
            COALESCE(p.asset_id, x1.asset_id) AS asset_id,
            COALESCE(p.d1_device_id, x1.d1_device_id) AS d1_device_id,
            COALESCE(p.measr_comp_id, x1.measr_comp_id) AS measr_comp_id,
            COALESCE(p.contact_id, x1.contact_id) AS contact_id,
            1 AS rn
        FROM todo_fk_pivot p
        LEFT JOIN cisadm.ci_case cs
            ON cs.case_id = p.case_id
        LEFT JOIN cisadm.ci_sp sp
            ON sp.sp_id = p.sp_id
        -- Optional FK enrichment when X1_BI_TD_ENTRY_VW exists; comment out on clients without this view.
        LEFT JOIN cisadm.x1_bi_td_entry_vw x1
            ON x1.td_entry_id = p.td_entry_id
    ),
    todo_rows AS (
        SELECT
            'TODO' AS queue_source,
            CAST(td.td_entry_id AS VARCHAR2(40)) AS queue_natural_key,
            td.cre_dttm AS queue_anchor_dttm,
            CAST(td.td_entry_id AS VARCHAR2(40)) AS td_entry_id,
            CAST(td.td_type_cd AS VARCHAR2(48)) AS td_type_cd,
            td_type_l.descr AS td_type_desc,
            CAST(td.entry_status_flg AS VARCHAR2(8)) AS entry_status_flg,
            entry_status_l.descr AS entry_status_desc,
            CAST(td.td_priority_flg AS VARCHAR2(8)) AS td_priority_flg,
            td_priority_l.descr AS td_priority_desc,
            CAST(td.role_id AS VARCHAR2(40)) AS role_id,
            role_l.descr AS role_desc,
            CAST(td.assigned_to AS VARCHAR2(40)) AS assigned_to,
            assigned_to_user.first_name || ' ' || assigned_to_user.last_name AS assigned_to_name,
            CAST(td.assigned_user_id AS VARCHAR2(40)) AS assigned_user_id,
            assigned_by_user.first_name || ' ' || assigned_by_user.last_name AS assigned_user_name,
            CAST(td.complete_user_id AS VARCHAR2(40)) AS complete_user_id,
            complete_user.first_name || ' ' || complete_user.last_name AS complete_user_name,
            td.cre_dttm AS td_cre_dttm,
            td.assigned_dttm,
            td.complete_dttm,
            CAST(td.batch_cd AS VARCHAR2(40)) AS td_batch_cd,
            td.batch_nbr AS td_batch_nbr,
            td.message_cat_nbr,
            td.message_nbr,
            msg_l.message_text,
            td.comments AS td_comments,
            CAST(TRUNC(SYSDATE) - TRUNC(CAST(td.cre_dttm AS DATE)) AS NUMBER(18,0)) AS days_old,
            CAST(
                CASE
                    WHEN td.entry_status_flg = 'W' THEN
                        ROUND(CAST(CURRENT_DATE AS DATE) - CAST(td.assigned_dttm AS DATE), 0)
                    WHEN td.entry_status_flg = 'C' THEN
                        ROUND(CAST(td.complete_dttm AS DATE) - CAST(td.assigned_dttm AS DATE), 0)
                    ELSE
                        0
                END AS NUMBER(18,4)
            ) AS assigned_tm_days,
            CAST(
                CASE
                    WHEN td.entry_status_flg = 'W' THEN
                        ROUND(CAST(CURRENT_DATE AS DATE) - CAST(td.assigned_dttm AS DATE), 2) * 24 * 60
                    WHEN td.entry_status_flg = 'C' THEN
                        ROUND(CAST(td.complete_dttm AS DATE) - CAST(td.assigned_dttm AS DATE), 2) * 24 * 60
                    ELSE
                        0
                END AS NUMBER(18,4)
            ) AS assigned_tm_mins,
            CAST(
                CASE
                    WHEN td.entry_status_flg = 'C' THEN
                        ROUND(CAST(td.complete_dttm AS DATE) - CAST(td.cre_dttm AS DATE), 0)
                    ELSE
                        0
                END AS NUMBER(18,4)
            ) AS complete_tm_days,
            CAST(
                CASE
                    WHEN td.entry_status_flg = 'C' THEN
                        ROUND(CAST(td.complete_dttm AS DATE) - CAST(td.cre_dttm AS DATE), 2) * 24 * 60
                    ELSE
                        0
                END AS NUMBER(18,4)
            ) AS complete_tm_mins,
            CAST(
                CASE
                    WHEN td.entry_status_flg = 'O' THEN
                        ROUND(CAST(CURRENT_DATE AS DATE) - CAST(td.cre_dttm AS DATE), 0)
                    ELSE
                        ROUND(CAST(td.assigned_dttm AS DATE) - CAST(td.cre_dttm AS DATE), 0)
                END AS NUMBER(18,4)
            ) AS unassigned_tm_days,
            CAST(
                CASE
                    WHEN td.entry_status_flg = 'O' THEN
                        ROUND(CAST(CURRENT_DATE AS DATE) - CAST(td.cre_dttm AS DATE), 2) * 24 * 60
                    ELSE
                        ROUND(CAST(td.assigned_dttm AS DATE) - CAST(td.cre_dttm AS DATE), 2) * 24 * 60
                END AS NUMBER(18,4)
            ) AS unassigned_tm_mins,
            CAST(fk.acct_id AS VARCHAR2(40)) AS fk_acct_id,
            CAST(fk.sa_id AS VARCHAR2(40)) AS fk_sa_id,
            CAST(fk.prem_id AS VARCHAR2(40)) AS fk_prem_id,
            CAST(fk.per_id AS VARCHAR2(40)) AS fk_per_id,
            CAST(fk.d1_sp_id AS VARCHAR2(40)) AS fk_d1_sp_id,
            CAST(fk.us_id AS VARCHAR2(40)) AS fk_us_id,
            CAST(fk.asset_id AS VARCHAR2(40)) AS fk_asset_id,
            CAST(fk.d1_device_id AS VARCHAR2(40)) AS fk_d1_device_id,
            CAST(fk.measr_comp_id AS VARCHAR2(40)) AS fk_measr_comp_id,
            CAST(fk.contact_id AS VARCHAR2(40)) AS fk_contact_id,
            pn.entity_name_upr AS person_name_upr,
            prem.address1 AS prem_address1,
            prem.address1_upr AS prem_address1_upr,
            prem.city AS prem_city,
            CAST(prem.state AS VARCHAR2(12)) AS prem_state,
            CAST(prem.postal AS VARCHAR2(24)) AS prem_postal,
            CAST(prem.prem_type_cd AS VARCHAR2(40)) AS prem_type_cd,
            prem_type_l.descr AS prem_type_desc,
            CAST(prem.trend_area_cd AS VARCHAR2(40)) AS trend_area_cd,
            trend_area_l.descr AS trend_area_desc,
            CAST(prem.time_zone_cd AS VARCHAR2(40)) AS time_zone_cd,
            time_zone_l.descr AS time_zone_desc,
            CAST(SUBSTR(prem.postal, 1, 5) AS VARCHAR2(12)) AS postal_5,
            CAST(NULL AS NUMBER) AS scheduler_id,
            CAST(NULL AS VARCHAR2(40)) AS batch_cd,
            CAST(NULL AS VARCHAR2(240)) AS batch_cd_desc,
            CAST(NULL AS NUMBER) AS batch_nbr,
            CAST(NULL AS NUMBER) AS batch_rerun_nbr,
            CAST(NULL AS NUMBER) AS batch_thread_nbr,
            CAST(NULL AS DATE) AS batch_bus_dt,
            CAST(NULL AS TIMESTAMP) AS batch_start_dttm,
            CAST(NULL AS TIMESTAMP) AS batch_end_dttm,
            CAST(NULL AS VARCHAR2(8)) AS batch_run_status,
            CAST(NULL AS VARCHAR2(240)) AS batch_run_status_desc,
            CAST(NULL AS VARCHAR2(4)) AS batch_do_not_restart_sw,
            CAST(NULL AS VARCHAR2(8)) AS thread_status,
            CAST(NULL AS VARCHAR2(240)) AS thread_status_desc,
            CAST(NULL AS VARCHAR2(254)) AS thread_log_file_name,
            CAST(NULL AS NUMBER) AS thread_retry_cnt,
            CAST(NULL AS NUMBER) AS rec_proc_cnt,
            CAST(NULL AS NUMBER) AS rec_err_cnt,
            CAST(NULL AS TIMESTAMP) AS inst_start_dttm,
            CAST(NULL AS TIMESTAMP) AS inst_end_dttm,
            CAST(NULL AS VARCHAR2(4000)) AS inst_file_details,
            CAST(NULL AS NUMBER(18,4)) AS duration_hours,
            CAST(NULL AS NUMBER(18,4)) AS duration_mins
        FROM cisadm.ci_td_entry td
        LEFT JOIN todo_fk_ranked fk
            ON fk.td_entry_id = td.td_entry_id
           AND fk.rn = 1
        LEFT JOIN cisadm.ci_per_name pn
            ON pn.per_id = fk.per_id
           AND pn.name_type_flg = 'PRIM'
        LEFT JOIN cisadm.ci_prem prem
            ON prem.prem_id = fk.prem_id
        LEFT JOIN cisadm.sc_user assigned_to_user
            ON assigned_to_user.user_id = td.assigned_to
        LEFT JOIN cisadm.sc_user assigned_by_user
            ON assigned_by_user.user_id = td.assigned_user_id
        LEFT JOIN cisadm.sc_user complete_user
            ON complete_user.user_id = td.complete_user_id
        LEFT JOIN cisadm.ci_td_type_l td_type_l
            ON td_type_l.td_type_cd = td.td_type_cd
           AND td_type_l.language_cd = 'ENG'
        LEFT JOIN cisadm.ci_lookup_val_l entry_status_l
            ON TRIM(entry_status_l.field_name) = 'ENTRY_STATUS_FLG'
           AND TRIM(entry_status_l.field_value) = TRIM(td.entry_status_flg)
           AND entry_status_l.language_cd = 'ENG'
        LEFT JOIN cisadm.ci_lookup_val_l td_priority_l
            ON TRIM(td_priority_l.field_name) = 'TD_PRIORITY_FLG'
           AND TRIM(td_priority_l.field_value) = TRIM(td.td_priority_flg)
           AND td_priority_l.language_cd = 'ENG'
        LEFT JOIN cisadm.ci_role_l role_l
            ON role_l.role_id = td.role_id
           AND role_l.language_cd = 'ENG'
        LEFT JOIN cisadm.ci_msg_l msg_l
            ON msg_l.message_cat_nbr = td.message_cat_nbr
           AND msg_l.message_nbr = td.message_nbr
           AND msg_l.language_cd = 'ENG'
        LEFT JOIN cisadm.ci_prem_type_l prem_type_l
            ON prem_type_l.prem_type_cd = prem.prem_type_cd
           AND prem_type_l.language_cd = 'ENG'
        LEFT JOIN cisadm.ci_trend_area_l trend_area_l
            ON trend_area_l.trend_area_cd = prem.trend_area_cd
           AND trend_area_l.language_cd = 'ENG'
        LEFT JOIN cisadm.ci_time_zone_l time_zone_l
            ON time_zone_l.time_zone_cd = prem.time_zone_cd
           AND time_zone_l.language_cd = 'ENG'
    ),
    batch_rows AS (
        SELECT
            'BATCH' AS queue_source,
            TO_CHAR(inst.scheduler_id) AS queue_natural_key,
            inst.start_dttm AS queue_anchor_dttm,
            CAST(NULL AS VARCHAR2(40)) AS td_entry_id,
            CAST(NULL AS VARCHAR2(48)) AS td_type_cd,
            CAST(NULL AS VARCHAR2(240)) AS td_type_desc,
            CAST(NULL AS VARCHAR2(8)) AS entry_status_flg,
            CAST(NULL AS VARCHAR2(240)) AS entry_status_desc,
            CAST(NULL AS VARCHAR2(8)) AS td_priority_flg,
            CAST(NULL AS VARCHAR2(240)) AS td_priority_desc,
            CAST(NULL AS VARCHAR2(40)) AS role_id,
            CAST(NULL AS VARCHAR2(240)) AS role_desc,
            CAST(NULL AS VARCHAR2(40)) AS assigned_to,
            CAST(NULL AS VARCHAR2(200)) AS assigned_to_name,
            CAST(NULL AS VARCHAR2(40)) AS assigned_user_id,
            CAST(NULL AS VARCHAR2(200)) AS assigned_user_name,
            CAST(NULL AS VARCHAR2(40)) AS complete_user_id,
            CAST(NULL AS VARCHAR2(200)) AS complete_user_name,
            CAST(NULL AS TIMESTAMP) AS td_cre_dttm,
            CAST(NULL AS TIMESTAMP) AS assigned_dttm,
            CAST(NULL AS TIMESTAMP) AS complete_dttm,
            CAST(NULL AS VARCHAR2(40)) AS td_batch_cd,
            CAST(NULL AS NUMBER) AS td_batch_nbr,
            CAST(NULL AS NUMBER) AS message_cat_nbr,
            CAST(NULL AS NUMBER) AS message_nbr,
            CAST(NULL AS VARCHAR2(4000)) AS message_text,
            CAST(NULL AS VARCHAR2(4000)) AS td_comments,
            CAST(NULL AS NUMBER(18,0)) AS days_old,
            CAST(NULL AS NUMBER(18,4)) AS assigned_tm_days,
            CAST(NULL AS NUMBER(18,4)) AS assigned_tm_mins,
            CAST(NULL AS NUMBER(18,4)) AS complete_tm_days,
            CAST(NULL AS NUMBER(18,4)) AS complete_tm_mins,
            CAST(NULL AS NUMBER(18,4)) AS unassigned_tm_days,
            CAST(NULL AS NUMBER(18,4)) AS unassigned_tm_mins,
            CAST(NULL AS VARCHAR2(40)) AS fk_acct_id,
            CAST(NULL AS VARCHAR2(40)) AS fk_sa_id,
            CAST(NULL AS VARCHAR2(40)) AS fk_prem_id,
            CAST(NULL AS VARCHAR2(40)) AS fk_per_id,
            CAST(NULL AS VARCHAR2(40)) AS fk_d1_sp_id,
            CAST(NULL AS VARCHAR2(40)) AS fk_us_id,
            CAST(NULL AS VARCHAR2(40)) AS fk_asset_id,
            CAST(NULL AS VARCHAR2(40)) AS fk_d1_device_id,
            CAST(NULL AS VARCHAR2(40)) AS fk_measr_comp_id,
            CAST(NULL AS VARCHAR2(40)) AS fk_contact_id,
            CAST(NULL AS VARCHAR2(200)) AS person_name_upr,
            CAST(NULL AS VARCHAR2(254)) AS prem_address1,
            CAST(NULL AS VARCHAR2(254)) AS prem_address1_upr,
            CAST(NULL AS VARCHAR2(90)) AS prem_city,
            CAST(NULL AS VARCHAR2(12)) AS prem_state,
            CAST(NULL AS VARCHAR2(24)) AS prem_postal,
            CAST(NULL AS VARCHAR2(40)) AS prem_type_cd,
            CAST(NULL AS VARCHAR2(240)) AS prem_type_desc,
            CAST(NULL AS VARCHAR2(40)) AS trend_area_cd,
            CAST(NULL AS VARCHAR2(240)) AS trend_area_desc,
            CAST(NULL AS VARCHAR2(40)) AS time_zone_cd,
            CAST(NULL AS VARCHAR2(240)) AS time_zone_desc,
            CAST(NULL AS VARCHAR2(12)) AS postal_5,
            inst.scheduler_id,
            CAST(inst.batch_cd AS VARCHAR2(40)) AS batch_cd,
            batch_ctrl_l.descr AS batch_cd_desc,
            inst.batch_nbr,
            inst.batch_rerun_nbr,
            inst.batch_thread_nbr,
            run.batch_bus_dt,
            run.start_dttm AS batch_start_dttm,
            run.end_dttm AS batch_end_dttm,
            CAST(run.run_status AS VARCHAR2(8)) AS batch_run_status,
            run_status_l.descr AS batch_run_status_desc,
            CAST(run.do_not_restart_sw AS VARCHAR2(4)) AS batch_do_not_restart_sw,
            CAST(thd.thread_status AS VARCHAR2(8)) AS thread_status,
            thread_status_l.descr AS thread_status_desc,
            CAST(thd.log_file_name AS VARCHAR2(254)) AS thread_log_file_name,
            thd.thd_retry_cnt AS thread_retry_cnt,
            inst.rec_proc_cnt,
            inst.rec_err_cnt,
            inst.start_dttm AS inst_start_dttm,
            inst.end_dttm AS inst_end_dttm,
            CAST(inst.file_details AS VARCHAR2(4000)) AS inst_file_details,
            CAST(ROUND((CAST(inst.end_dttm AS DATE) - CAST(inst.start_dttm AS DATE)) * 24, 4) AS NUMBER(18,4)) AS duration_hours,
            CAST(ROUND((CAST(inst.end_dttm AS DATE) - CAST(inst.start_dttm AS DATE)) * 24 * 60) AS NUMBER(18,4)) AS duration_mins
        FROM cisadm.ci_batch_inst inst
        JOIN cisadm.ci_batch_run run
            ON run.batch_cd = inst.batch_cd
           AND run.batch_nbr = inst.batch_nbr
           AND run.batch_rerun_nbr = inst.batch_rerun_nbr
        JOIN cisadm.ci_batch_thd thd
            ON thd.batch_cd = inst.batch_cd
           AND thd.batch_nbr = inst.batch_nbr
           AND thd.batch_rerun_nbr = inst.batch_rerun_nbr
           AND thd.batch_thread_nbr = inst.batch_thread_nbr
        LEFT JOIN cisadm.ci_batch_ctrl_l batch_ctrl_l
            ON batch_ctrl_l.batch_cd = inst.batch_cd
           AND batch_ctrl_l.language_cd = 'ENG'
        LEFT JOIN cisadm.ci_lookup_val_l run_status_l
            ON TRIM(run_status_l.field_name) = 'RUN_STATUS'
           AND TRIM(run_status_l.field_value) = TRIM(run.run_status)
           AND run_status_l.language_cd = 'ENG'
        LEFT JOIN cisadm.ci_lookup_val_l thread_status_l
            ON TRIM(thread_status_l.field_name) = 'THREAD_STATUS'
           AND TRIM(thread_status_l.field_value) = TRIM(thd.thread_status)
           AND thread_status_l.language_cd = 'ENG'
    )
    SELECT
        src.*,
        v_load_dttm
    FROM (
        SELECT * FROM todo_rows
        UNION ALL
        SELECT * FROM batch_rows
    ) src;

    COMMIT;
END;
/
