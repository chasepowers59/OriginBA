CREATE OR REPLACE PROCEDURE cisadm.refresh_crew_ops_rpt_curr AS
    v_load_dttm TIMESTAMP := SYSTIMESTAMP;
BEGIN
    EXECUTE IMMEDIATE 'TRUNCATE TABLE cisadm.crew_ops_rpt_curr';

    INSERT INTO cisadm.crew_ops_rpt_curr (
        crew_id,
        crew_name,
        crew_type_flg,
        crew_type_desc,
        bo_status_cd,
        bo_status_desc,
        bo_status_reason_cd,
        bo_status_reason_desc,
        bus_obj_cd,
        bus_obj_desc,
        rep_cre_dttm,
        status_upd_dttm,
        nt_xid_cd,
        nt_xid_desc,
        per_id,
        user_id,
        user_name,
        svc_area,
        worker_capability,
        fa_activity_count,
        completed_fa_count,
        open_fa_count,
        distinct_fa_type_count,
        latest_fa_id,
        latest_fa_cre_dttm,
        latest_fa_start_dttm,
        latest_fa_end_dttm,
        latest_fa_status_cd,
        latest_fa_status_desc,
        latest_fa_type_cd,
        latest_fa_type_desc,
        latest_appointment_flg,
        oldest_open_fa_days,
        avg_days_to_complete,
        load_dttm
    )
    WITH
    fa_crew_link AS (
        SELECT
            ch.srch_char_val AS crew_id,
            act.d1_activity_id,
            act.activity_type_cd,
            act.bo_status_cd,
            act.cre_dttm,
            act.start_dttm,
            act.end_dttm,
            boda.appointment_flg,
            CASE
                WHEN act.bo_status_cd IN ('COMPLETED', 'DISCARDED') THEN 1
                ELSE 0
            END AS is_completed,
            CASE
                WHEN act.end_dttm IS NOT NULL AND act.start_dttm IS NOT NULL
                THEN TRUNC(CAST(act.end_dttm AS DATE)) - TRUNC(CAST(act.start_dttm AS DATE))
            END AS days_to_complete,
            CASE
                WHEN act.bo_status_cd NOT IN ('COMPLETED', 'DISCARDED') AND act.cre_dttm IS NOT NULL
                THEN TRUNC(SYSDATE) - TRUNC(CAST(act.cre_dttm AS DATE))
            END AS open_fa_days
        FROM cisadm.d1_activity_char ch
        INNER JOIN cisadm.d1_activity act
            ON act.d1_activity_id = ch.d1_activity_id
        INNER JOIN cisadm.d1_activity_type act_type
            ON act_type.activity_type_cd = act.activity_type_cd
           AND act_type.activity_type_cat_flg = 'D1FA'
        LEFT JOIN cisadm.cms_d1_activity_d1fa_boda_vw boda
            ON boda.d1_activity_id = act.d1_activity_id
        WHERE ch.char_type_cd = 'CMFAREP'
    ),
    fa_rollup AS (
        SELECT
            link.crew_id,
            COUNT(DISTINCT link.d1_activity_id) AS fa_activity_count,
            COUNT(DISTINCT CASE WHEN link.is_completed = 1 THEN link.d1_activity_id END) AS completed_fa_count,
            COUNT(DISTINCT CASE WHEN link.is_completed = 0 THEN link.d1_activity_id END) AS open_fa_count,
            COUNT(DISTINCT link.activity_type_cd) AS distinct_fa_type_count,
            MAX(link.open_fa_days) AS oldest_open_fa_days,
            AVG(link.days_to_complete) AS avg_days_to_complete
        FROM fa_crew_link link
        GROUP BY link.crew_id
    ),
    latest_fa AS (
        SELECT
            picked.crew_id,
            picked.d1_activity_id,
            picked.cre_dttm,
            picked.start_dttm,
            picked.end_dttm,
            picked.bo_status_cd,
            picked.activity_type_cd,
            picked.appointment_flg
        FROM (
            SELECT
                link.crew_id,
                link.d1_activity_id,
                link.cre_dttm,
                link.start_dttm,
                link.end_dttm,
                link.bo_status_cd,
                link.activity_type_cd,
                link.appointment_flg,
                ROW_NUMBER() OVER (
                    PARTITION BY link.crew_id
                    ORDER BY link.cre_dttm DESC, link.d1_activity_id DESC
                ) AS rn
            FROM fa_crew_link link
        ) picked
        WHERE picked.rn = 1
    ),
    boda_one AS (
        SELECT
            boda.c1_representative_cd,
            boda.cm_ml_svc_area,
            boda.cm_ml_worker_capability,
            ROW_NUMBER() OVER (
                PARTITION BY boda.c1_representative_cd
                ORDER BY boda.c1_representative_cd
            ) AS rn
        FROM cisadm.cms_c1_representative_boda_vw boda
    )
    SELECT
        rep.c1_representative_cd,
        rep_l.descr100,
        rep.c1_representative_type_flg,
        rep_type_l.descr,
        rep.bo_status_cd,
        NVL(rep_status_l.descr, rep.bo_status_cd),
        rep.bo_status_reason_cd,
        rep_status_rsn_l.descr,
        rep.bus_obj_cd,
        rep_bus_obj_l.descr,
        rep.cre_dttm,
        rep.status_upd_dttm,
        rep.nt_xid_cd,
        nt_xid_l.descr50,
        rep.per_id,
        rep.user_id,
        TRIM(sc_user.first_name || ' ' || sc_user.last_name),
        boda.cm_ml_svc_area,
        boda.cm_ml_worker_capability,
        NVL(fa_roll.fa_activity_count, 0),
        NVL(fa_roll.completed_fa_count, 0),
        NVL(fa_roll.open_fa_count, 0),
        NVL(fa_roll.distinct_fa_type_count, 0),
        latest_fa.d1_activity_id,
        latest_fa.cre_dttm,
        latest_fa.start_dttm,
        latest_fa.end_dttm,
        latest_fa.bo_status_cd,
        latest_fa_status_l.descr,
        latest_fa.activity_type_cd,
        latest_fa_type_l.descr100,
        latest_fa.appointment_flg,
        fa_roll.oldest_open_fa_days,
        fa_roll.avg_days_to_complete,
        v_load_dttm
    FROM cisadm.c1_representative rep
    LEFT JOIN boda_one boda
        ON boda.c1_representative_cd = rep.c1_representative_cd
       AND boda.rn = 1
    LEFT JOIN fa_rollup fa_roll
        ON fa_roll.crew_id = rep.c1_representative_cd
    LEFT JOIN latest_fa
        ON latest_fa.crew_id = rep.c1_representative_cd
    LEFT JOIN cisadm.c1_representative_l rep_l
        ON rep_l.c1_representative_cd = rep.c1_representative_cd
       AND rep_l.language_cd = 'ENG'
    LEFT JOIN cisadm.f1_bus_obj_l rep_bus_obj_l
        ON rep_bus_obj_l.bus_obj_cd = rep.bus_obj_cd
       AND rep_bus_obj_l.language_cd = 'ENG'
    LEFT JOIN cisadm.f1_bus_obj_status_l rep_status_l
        ON rep_status_l.bus_obj_cd = rep.bus_obj_cd
       AND rep_status_l.bo_status_cd = rep.bo_status_cd
       AND rep_status_l.language_cd = 'ENG'
    LEFT JOIN cisadm.f1_bus_obj_status_rsn_l rep_status_rsn_l
        ON rep_status_rsn_l.bo_status_reason_cd = rep.bo_status_reason_cd
       AND rep_status_rsn_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l rep_type_l
        ON TRIM(rep_type_l.field_name) = 'C1_REPRESENTATIVE_TYPE_FLG'
       AND TRIM(rep_type_l.field_value) = TRIM(rep.c1_representative_type_flg)
       AND rep_type_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_nt_xid_l nt_xid_l
        ON nt_xid_l.nt_xid_cd = rep.nt_xid_cd
       AND nt_xid_l.language_cd = 'ENG'
    LEFT JOIN cisadm.sc_user sc_user
        ON sc_user.user_id = rep.user_id
    LEFT JOIN cisadm.f1_bus_obj_status_l latest_fa_status_l
        ON latest_fa_status_l.bus_obj_cd = 'D1-Activity'
       AND latest_fa_status_l.bo_status_cd = latest_fa.bo_status_cd
       AND latest_fa_status_l.language_cd = 'ENG'
    LEFT JOIN cisadm.d1_activity_type_l latest_fa_type_l
        ON latest_fa_type_l.activity_type_cd = latest_fa.activity_type_cd
       AND latest_fa_type_l.language_cd = 'ENG';

    COMMIT;
END;
/
