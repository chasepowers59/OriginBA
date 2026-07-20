CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_BI_ACTIVITY_VW" ("ACT_ID", "BO_STATUS_CD", "BO_STATUS_REASON_CD", "CRE_DTTM", "USER_ID", "DESCR100", "ACT_TYPE_CD", "PRNT_ACT_ID", "NODE_ID", "ASSET_ID", "WO_ID", "ACTVN_DTTM", "WORK_WIN_START_DTTM", "WORK_WIN_END_DTTM", "ACT_DPOS_FLG", "SERVICE_CLASS_CD", "WORK_REQ_ID", "REQUESTOR_ID", "DELIVER_TO_LOC", "W1_CREW_ID", "PHASE_FLG", "WORK_PRIORITY_FLG", "DESCRLONG", "TMPL_ACT_ID", "PRJ_ID", "OUTAGE_TYPE_FLG", "BACK_LOG_GRP_FLG", "HELD_FOR_PARTS_FLG", "MAT_DISP_ID", "MAINT_SCHED_ID", "MAINT_TRIGGER_ID", "MEASUREMENT_ID", "ORIGINAL_WORK_DT", "ANNIVERSARY_DT", "ANNIVERSARY_VALUE", "MEASUREMENT_UOM_CD", "EMERGENCY_FLG", "ACT_NUM", "PLANNER_CD", "MAINT_EVENT_ID", "APPROVAL_PROF_CD", "WORK_LOC_ID", "TOTAL_PRIORITY", "WORK_CLASS_CD", "WORK_CATEGORY_CD", "COMPLIANCE_TYPE_CD", "COMPLIANCE_DATE", "COMPLIANCE_UPD_DATE_RSN_FLG", "SVC_HIST_ID", "SEQ_NUM", "OWNING_ACCESS_GRP_CD", "REQUIRED_BY_DT", "ACT_CNT", "FIELD_ACT_CNT", "CONSTR_ACT_CNT", "MAINT_ACT_CNT", "CM_ACT_CNT", "PM_ACT_CNT", "OVERDUE_ACT_CNT", "OVERDUE_MAINT_ACT_CNT", "OVERDUE_CONSTR_ACT_CNT", "OVERDUE_FIELD_ACT_CNT", "OVERDUE_PM_ACT_CNT", "CYCLES_OVERDUE_PM_ACT_CNT", "OVERDUE_CM_ACT_CNT", "OPEN_ACT_CNT", "OPEN_MAINT_ACT_CNT", "OPEN_CONSTR_ACT_CNT", "PLANNED_ACT_CNT", "WAIT_SCHED_ACT_CNT", "HELD_MAINT_ACT_CNT", "HELD_CM_ACT_CNT", "HELD_PM_ACT_CNT", "HELD_COMPLIANCE_ACT_CNT", "HELD_CONSTR_ACT_CNT", "COMPLIANCE_ACT_CNT", "OPEN_COMPLIANCE_ACT_CNT", "DUE_1WK_OPEN_COMPL_ACT_CNT", "DUE_30DY_OPEN_COMPL_ACT_CNT", "LATE_OPEN_COMPL_ACT_CNT", "LATE_CMPL_COMPL_ACT_CNT", "ONTIME_CMPL_COMPL_ACT_CNT") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
     act_id,
     bo_status_cd,
     bo_status_reason_cd,
     cre_dttm,
     user_id,
     descr100,
     act_type_cd,
     prnt_act_id,
     node_id,
     asset_id,
     wo_id,
     actvn_dttm,
     work_win_start_dttm,
     work_win_end_dttm,
     act_dpos_flg,
     service_class_cd,
     work_req_id,
     requestor_id,
     deliver_to_loc,
     w1_crew_id,
     phase_flg,
     work_priority_flg,
     descrlong,
     tmpl_act_id,
     prj_id,
     outage_type_flg,
     back_log_grp_flg,
     held_for_parts_flg,
     mat_disp_id,
     maint_sched_id,
     maint_trigger_id,
     measurement_id,
     original_work_dt,
     anniversary_dt,
     anniversary_value,
     measurement_uom_cd,
     emergency_flg,
     act_num,
     planner_cd,
     maint_event_id,
     approval_prof_cd,
     work_loc_id,
     total_priority,
     work_class_cd,
     work_category_cd,
     compliance_type_cd,
     compliance_date,
     compliance_upd_date_rsn_flg,
     svc_hist_id,
     seq_num,
     owning_access_grp_cd,
     required_by_dt,
     act_cnt,
     field_act_cnt,
     constr_act_cnt,
     maint_act_cnt,
     cm_act_cnt,
     pm_act_cnt,
     overdue_act_cnt,
     CASE
         WHEN maint_act_cnt = 1
              AND overdue_act_cnt = 1 THEN 1
         ELSE 0
     END AS overdue_maint_act_cnt,
     CASE
         WHEN constr_act_cnt = 1
              AND overdue_act_cnt = 1 THEN 1
         ELSE 0
     END AS overdue_constr_act_cnt,
     CASE
         WHEN field_act_cnt = 1
              AND overdue_act_cnt = 1 THEN 1
         ELSE 0
     END AS overdue_field_act_cnt,
     CASE
         WHEN pm_act_cnt = 1
              AND overdue_act_cnt = 1 THEN 1
         ELSE 0
     END AS overdue_pm_act_cnt,
     CASE
         WHEN open_act_cnt = 1
              AND pm_act_cnt = 1
              AND overdue_no_stat_act_cnt = 1 THEN nvl( (
             SELECT
                 CASE
                     WHEN(mt.f1_years > 0
                            OR mt.f1_months > 0)
                          AND mt.f1_days = 0 THEN floor(months_between(current_date,original_work_dt) / (f1_years * 12 + f1_months
                          ) )
                     ELSE floor( (current_date - original_work_dt) / (f1_years * 365 + f1_months * 30 + f1_days) )
                 END
             FROM
                 w1_maint_trigger mt
             WHERE
                 mt.maint_trigger_id = a.maint_trigger_id
                 AND mt.trigger_type_flg IN(
                     'W1CA','W1CI'
                 )
         ),0)
         ELSE 0
     END AS cycles_overdue_pm_act_cnt,
     CASE
         WHEN cm_act_cnt = 1
              AND overdue_act_cnt = 1 THEN 1
         ELSE 0
     END AS overdue_cm_act_cnt,
     open_act_cnt,
     CASE
         WHEN maint_act_cnt = 1
              AND open_act_cnt = 1 THEN 1
         ELSE 0
     END AS open_maint_act_cnt,
     CASE
         WHEN constr_act_cnt = 1
              AND open_act_cnt = 1 THEN 1
         ELSE 0
     END AS open_constr_act_cnt,
     planned_act_cnt,
     wait_sched_act_cnt,
     CASE
         WHEN maint_act_cnt = 1
              AND planned_act_cnt = 1
              AND held_for_parts_flg = 'W1YS' THEN 1
         ELSE 0
     END AS held_maint_act_cnt,
     CASE
         WHEN cm_act_cnt = 1
              AND planned_act_cnt = 1
              AND held_for_parts_flg = 'W1YS' THEN 1
         ELSE 0
     END AS held_cm_act_cnt,
     CASE
         WHEN pm_act_cnt = 1
              AND planned_act_cnt = 1
              AND held_for_parts_flg = 'W1YS' THEN 1
         ELSE 0
     END AS held_pm_act_cnt,
     CASE
         WHEN compliance_act_cnt = 1
              AND planned_act_cnt = 1
              AND held_for_parts_flg = 'W1YS' THEN 1
         ELSE 0
     END AS held_compliance_act_cnt,
     CASE
         WHEN constr_act_cnt = 1
              AND planned_act_cnt = 1
              AND held_for_parts_flg = 'W1YS' THEN 1
         ELSE 0
     END AS held_constr_act_cnt,
     compliance_act_cnt,
     CASE
         WHEN compliance_act_cnt = 1
              AND open_act_cnt = 1 THEN 1
         ELSE 0
     END AS open_compliance_act_cnt,
     CASE
         WHEN compliance_act_cnt = 1
              AND open_act_cnt = 1
              AND compliance_date - current_date <= 7 THEN 1
         ELSE 0
     END AS due_1wk_open_compl_act_cnt,
     CASE
         WHEN compliance_act_cnt = 1
              AND open_act_cnt = 1
              AND compliance_date - current_date <= 30 THEN 1
         ELSE 0
     END AS due_30dy_open_compl_act_cnt,
     CASE
         WHEN compliance_act_cnt = 1
              AND open_act_cnt = 1
              AND compliance_date < current_date THEN 1
         ELSE 0
     END AS late_open_compl_act_cnt,
     CASE
         WHEN compliance_act_cnt = 1
              AND completed_act_cnt = 1
              AND compliance_date < completion_dt THEN 1
         ELSE 0
     END AS late_cmpl_compl_act_cnt,
     CASE
         WHEN compliance_act_cnt = 1
              AND completed_act_cnt = 1
              AND compliance_date >= completion_dt THEN 1
         ELSE 0
     END AS ontime_cmpl_compl_act_cnt
 FROM
     (
         SELECT
             ac.act_id,
             ac.bo_status_cd,
             ac.bo_status_reason_cd,
             ac.cre_dttm,
             ac.user_id,
             ac.descr100,
             ac.act_type_cd,
             ac.prnt_act_id,
             ac.node_id,
             ac.asset_id,
             ac.wo_id,
             ac.actvn_dttm,
             ac.work_win_start_dttm,
             ac.work_win_end_dttm,
             ac.act_dpos_flg,
             ac.service_class_cd,
             ac.work_req_id,
             ac.requestor_id,
             ac.deliver_to_loc,
             ac.w1_crew_id,
             ac.phase_flg,
             ac.work_priority_flg,
             ac.descrlong,
             ac.tmpl_act_id,
             ac.prj_id,
             ac.outage_type_flg,
             ac.back_log_grp_flg,
             ac.held_for_parts_flg,
             ac.mat_disp_id,
             ac.maint_sched_id,
             ac.maint_trigger_id,
             ac.measurement_id,
             ac.original_work_dt,
             ac.anniversary_dt,
             ac.anniversary_value,
             ac.measurement_uom_cd,
             ac.emergency_flg,
             ac.act_num,
             ac.planner_cd,
             ac.maint_event_id,
             ac.approval_prof_cd,
             ac.work_loc_id,
             ac.total_priority,
             ac.work_class_cd,
             ac.work_category_cd,
             ac.compliance_type_cd,
             ac.compliance_date,
             ac.compliance_upd_date_rsn_flg,
             ac.svc_hist_id,
             ac.seq_num,
             ac.owning_access_grp_cd,
             ac.required_by_dt,
             act.constr_related_flg,
             wo.work_type_flg,
             1 AS act_cnt,
             CASE
                 WHEN act.category_flg = 'W1FA' THEN 1
                 ELSE 0
             END AS field_act_cnt,
             CASE
                 WHEN act.constr_related_flg = 'W1YS' THEN 1
                 ELSE 0
             END AS constr_act_cnt,
             CASE
                 WHEN wo.wo_id IS NOT NULL
                      AND wo.work_type_flg IN (
                     'W1PM',
                     'W1RG'
                 ) THEN 1
                 ELSE 0
             END AS maint_act_cnt,
             CASE
                 WHEN wo.wo_id IS NOT NULL
                      AND wo.work_type_flg = 'W1PM' THEN 1
                 ELSE 0
             END AS pm_act_cnt,
             CASE
                 WHEN wo.wo_id IS NOT NULL
                      AND wo.work_type_flg = 'W1RG' THEN 1
                 ELSE 0
             END AS cm_act_cnt,
             CASE
                 WHEN act.category_flg = 'W1FA'
                      AND ac.bo_status_cd IN (
                     'WORK'
                 )
                      AND trunc(ac.work_win_end_dttm) < current_date THEN 1
                 WHEN ac.wo_id IS NOT NULL
                      AND ac.bo_status_cd IN (
                     'ACTIVE',
                     'INPROGRESS'
                 )
                      AND wo.work_type_flg = 'W1PM'
                      AND ac.original_work_dt < current_date THEN 1
                 WHEN ac.wo_id IS NOT NULL
                      AND ac.bo_status_cd IN (
                     'ACTIVE',
                     'INPROGRESS'
                 )
                      AND ac.required_by_dt < current_date THEN 1
                 ELSE 0
             END AS overdue_act_cnt,
             CASE
                 WHEN act.category_flg = 'W1FA'
                      AND trunc(ac.work_win_end_dttm) < current_date THEN 1
                 WHEN ac.wo_id IS NOT NULL
                      AND wo.work_type_flg = 'W1PM'
                      AND ac.original_work_dt < current_date THEN 1
                 WHEN ac.wo_id IS NOT NULL
                      AND ac.required_by_dt < current_date THEN 1
                 ELSE 0
             END AS overdue_no_stat_act_cnt,
             CASE
                 WHEN ac.bo_status_cd IN (
                     'PLANNING',
                     'PENDAPPROVAL',
                     'APPROVED',
                     'ACTIVE',
                     'INPROGRESS',
                     'PENDING',
                     'SENT',
                     'WORK'
                 ) THEN 1
                 ELSE 0
             END AS open_act_cnt,
             CASE
                 WHEN ac.bo_status_cd IN (
                     'APPROVED',
                     'ACTIVE'
                 )
                      AND (
                     SELECT
                         COUNT(*)
                     FROM
                         w1_act_resrc_reqmt arr,
                         w1_crew_shift_act_sched csa,
                         w1_crew_shift cs
                     WHERE
                         arr.act_id = ac.act_id
                         AND csa.act_resrc_reqmt_id = arr.act_resrc_reqmt_id
                         AND cs.crew_shift_id = csa.crew_shift_id
                         AND cs.bo_status_cd IN ( 'ACTIVE','PLANNING')
                 ) = 0 THEN 1
                 ELSE 0
             END AS wait_sched_act_cnt,
             CASE
                 WHEN ac.bo_status_cd IN (
                     'APPROVED',
                     'ACTIVE'
                 ) THEN 1
                 ELSE 0
             END AS planned_act_cnt,
             CASE
                 WHEN ac.bo_status_cd = 'COMPLETE' THEN 1
                 ELSE 0
             END AS completed_act_cnt,
             CASE
                 WHEN ac.bo_status_cd = 'COMPLETE' THEN trunc(ac.status_upd_dttm)
                 ELSE NULL
             END AS completion_dt,
             CASE
                 WHEN ac.compliance_type_cd IS NOT NULL THEN 1
                 ELSE 0
             END AS compliance_act_cnt
         FROM
             w1_activity ac
             JOIN w1_activity_type act ON act.act_type_cd = ac.act_type_cd
             LEFT OUTER JOIN w1_wo wo ON wo.wo_id = ac.wo_id
      )a;
