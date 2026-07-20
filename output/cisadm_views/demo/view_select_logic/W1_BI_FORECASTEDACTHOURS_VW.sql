-- SELECT logic for CISADM.W1_BI_FORECASTEDACTHOURS_VW
SELECT
     act_id,
     resrc_type_id,
     bo_status_cd,
     bo_status_reason_cd,
     user_id,
     descr100,
     act_type_cd,
     node_id,
     asset_id,
     wo_id,
     actvn_dttm,
     work_win_start_dttm,
     work_win_end_dttm,
     service_class_cd,
     w1_crew_id,
     work_priority_flg,
     tmpl_act_id,
     outage_type_flg,
     back_log_grp_flg,
     held_for_parts_flg,
     original_work_dt,
     emergency_flg,
     planner_cd,
     total_priority,
     work_class_cd,
     work_category_cd,
     required_by_dt,
     owning_access_grp_cd,
     1 as act_resrc_cnt,
     CASE
         WHEN planned_labor_hrs > actual_labor_hrs THEN planned_labor_hrs - actual_labor_hrs
         ELSE 0
     END AS open_act_fc_labor_hrs,
     CASE
         WHEN maint_act_cnt = 1
              AND planned_labor_hrs > actual_labor_hrs THEN planned_labor_hrs - actual_labor_hrs
         ELSE 0
     END AS maint_act_fc_labor_hrs,
     CASE
         WHEN constr_act_cnt = 1
              AND planned_labor_hrs > actual_labor_hrs THEN planned_labor_hrs - actual_labor_hrs
         ELSE 0
     END AS constr_act_fc_labor_hrs,
     CASE
         WHEN maint_act_cnt = 1
              AND wait_sched_act_cnt = 1
              AND planned_labor_hrs > actual_labor_hrs THEN planned_labor_hrs - actual_labor_hrs
         ELSE 0
     END AS unsched_maint_fc_labor_hrs
 FROM
     (
         SELECT
             ac.act_id,
             arr.resrc_type_id,
             ac.bo_status_cd,
             ac.bo_status_reason_cd,
             ac.user_id,
             ac.descr100,
             ac.tmpl_act_id,
             ac.node_id,
             ac.asset_id,
             ac.planner_cd,
             ac.wo_id,
             ac.act_type_cd,
             ac.service_class_cd,
             ac.emergency_flg,
             ac.held_for_parts_flg,
             ac.work_priority_flg,
             ac.total_priority,
             ac.outage_type_flg,
             ac.back_log_grp_flg,
             ac.work_class_cd,
             ac.work_category_cd,
             ac.w1_crew_id,
             ac.required_by_dt,
             ac.actvn_dttm,
             ac.work_win_start_dttm,
             ac.work_win_end_dttm,
             ac.owning_access_grp_cd,
             ac.original_work_dt,
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
                 WHEN ac.bo_status_cd IN (
                     'APPROVED',
                     'ACTIVE',
                     'INPROGRESS'
                 ) THEN 1
                 ELSE 0
             END AS active_act_cnt,
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
                         AND cs.bo_status_cd IN (
                             'ACTIVE',
                             'PLANNING'
                         )
                 ) = 0 THEN 1
                 ELSE 0
             END AS wait_sched_act_cnt,
             arr.w1_duration * arr.w1_quantity AS planned_labor_hrs,
             nvl( (
                 SELECT
                     SUM(hours)
                 FROM
                     w1_timesheet_detail tsd
                 WHERE
                     tsd.act_resrc_reqmt_id = arr.act_resrc_reqmt_id
                     AND tsd.bo_status_cd = 'POSTED'
             ),0) AS actual_labor_hrs
         FROM
             w1_activity ac
             JOIN w1_activity_type act ON act.act_type_cd = ac.act_type_cd
             JOIN w1_act_resrc_reqmt arr ON arr.act_id = ac.act_id
                                            AND NOT arr.bo_status_cd IN (
                 'FULFILLED',
                 'CANCELED'
             )
             JOIN w1_resrc_type rt ON rt.resrc_type_id = arr.resrc_type_id
                                      AND rt.w1_resrc_class_flg = 'W1CR'
             LEFT OUTER JOIN w1_wo wo ON wo.wo_id = ac.wo_id
         WHERE
             ac.bo_status_cd IN (
                 'PLANNING',
                 'PENDAPPROVAL',
                 'APPROVED',
                 'ACTIVE',
                 'INPROGRESS'
             )
     ) a
