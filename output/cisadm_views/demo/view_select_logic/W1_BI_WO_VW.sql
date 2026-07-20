-- SELECT logic for CISADM.W1_BI_WO_VW
SELECT
     wo_id,
     bo_status_cd,
     bo_status_reason_cd,
     cre_dttm,
     user_id,
     descr100,
     template_name,
     svc_hist_type_cd,
     svc_sched_wo_id,
     work_req_id,
     work_priority_flg,
     descrlong,
     prj_id,
     requestor_id,
     w1_crew_id,
     required_by_dt,
     work_type_flg,
     maint_sched_id,
     emergency_flg,
     wo_num,
     constr_related_flg,
     work_design_id,
     work_class_cd,
     work_category_cd,
     overhead_cd,
     planner_cd,
     owning_access_grp_cd,
     node_id,
     asset_id,
     wo_cre_dttm,
     finish_dttm,
     original_work_dt,
     constr_wo_cnt,
     maint_wo_cnt,
     pm_wo_cnt,
     cm_wo_cnt,

     CASE
         WHEN work_type_flg = 'W1PM'
              AND finish_dttm IS NOT NULL
              AND trunc(finish_dttm) <= original_work_dt THEN 1
         ELSE 0
     END AS adhered_pm_due_dt_cnt,
     CASE
         WHEN work_type_flg = 'W1RG'
              AND finish_dttm IS NOT NULL
              AND trunc(finish_dttm) <= required_by_dt THEN 1
         ELSE 0
     END AS adhered_cm_due_dt_cnt,
     CASE
         WHEN bo_status_cd <> 'CANCELED' THEN maint_wo_cnt
         ELSE 0
     END AS cre_maint_wo_cnt,
     CASE
         WHEN bo_status_cd IN (
             'COMPLETED',
             'CLOSED'
         ) THEN maint_wo_cnt
         ELSE 0
     END AS cmpl_maint_wo_cnt,
     CASE
         WHEN bo_status_cd <> 'CANCELED' THEN constr_wo_cnt
         ELSE 0
     END AS cre_constr_wo_cnt,
     CASE
         WHEN bo_status_cd IN (
             'COMPLETED',
             'CLOSED'
         ) THEN constr_wo_cnt
         ELSE 0
     END AS cmpl_constr_wo_cnt,
     open_wo_cnt,
     overdue_wo_cnt,
     CASE
         WHEN maint_wo_cnt = 1
              AND overdue_wo_cnt = 1 THEN 1
         ELSE 0
     END AS overdue_maint_wo_cnt,
     CASE
         WHEN constr_wo_cnt = 1
              AND overdue_wo_cnt = 1 THEN 1
         ELSE 0
     END AS overdue_constr_wo_cnt,
       
     CASE
         WHEN pm_wo_cnt = 1
              AND bo_status_cd = 'ACTIVE'
              AND original_work_dt < current_date THEN 1
         ELSE 0
     END AS overdue_pm_wo_cnt,
     CASE
         WHEN cm_wo_cnt = 1
              AND overdue_wo_cnt = 1 THEN 1
         ELSE 0
     END AS overdue_cm_wo_cnt,
     CASE
         WHEN open_wo_cnt = 1
              AND maint_wo_cnt = 1 THEN 1
         ELSE 0
     END AS open_maint_wo_cnt,
     CASE
         WHEN open_wo_cnt = 1
              AND constr_wo_cnt = 1 THEN 1
         ELSE 0
     END AS open_constr_wo_cnt,
     planned_wo_cnt,
     planning_wo_cnt,
     1 as wo_cnt
 FROM
     (
         SELECT
             wo_id,
             bo_status_cd,
             bo_status_reason_cd,
             cre_dttm,
             user_id,
             descr100,
             template_name,
             svc_hist_type_cd,
             svc_sched_wo_id,
             work_req_id,
             work_priority_flg,
             descrlong,
             prj_id,
             requestor_id,
             w1_crew_id,
             required_by_dt,
             work_type_flg,
             maint_sched_id,
             emergency_flg,
             wo_num,
             constr_related_flg,
             work_design_id,
             work_class_cd,
             work_category_cd,
             overhead_cd,
             planner_cd,
             owning_access_grp_cd,
             (
                 SELECT
                     ac.node_id
                 FROM
                     w1_activity ac
                 WHERE
                     ac.wo_id = wo.wo_id
                     AND ac.act_num = (
                         SELECT
                             MIN(ac2.act_num)
                         FROM
                             w1_activity ac2
                         WHERE
                             ac2.wo_id = ac.wo_id
                            AND ac2.bo_status_cd NOT IN('DISCARD','CANCELED','REJECTED')
                     )
             ) AS node_id,
             (
                 SELECT
                     ac.asset_id
                 FROM
                     w1_activity ac
                 WHERE
                     ac.wo_id = wo.wo_id
                     AND ac.act_num = (
                         SELECT
                             MIN(ac2.act_num)
                         FROM
                             w1_activity ac2
                         WHERE
                             ac2.wo_id = ac.wo_id
                             AND ac2.bo_status_cd NOT IN('DISCARD','CANCELED','REJECTED')
                     )
             ) AS asset_id,
             nvl2(wo.work_req_id, (
                 SELECT
                     wr.cre_dttm
                 FROM
                     w1_work_req wr
                 WHERE
                     wr.work_req_id = wo.work_req_id
             ),wo.cre_dttm) AS wo_cre_dttm,
             DECODE(TRIM(wo.bo_status_cd),'COMPLETED',wo.status_upd_dttm,(
                 SELECT
                     MAX(lg.log_dttm)
                 FROM
                     w1_wo_log lg
                 WHERE
                     lg.wo_id = wo.wo_id
                     AND lg.bo_status_cd = 'COMPLETED'
             ) ) AS finish_dttm,
             CASE
                 WHEN constr_related_flg = 'W1YS' THEN 1
                 ELSE 0
             END AS constr_wo_cnt,
             CASE
                 WHEN work_type_flg IN (
                     'W1PM',
                     'W1RG'
                 ) THEN 1
                 ELSE 0
             END AS maint_wo_cnt,
             CASE
                 WHEN work_type_flg = 'W1PM' THEN 1
                 ELSE 0
             END AS pm_wo_cnt,
             CASE
                 WHEN work_type_flg = 'W1RG' THEN 1
                 ELSE 0
             END AS cm_wo_cnt,
             (
                 SELECT
                     MIN(ac.original_work_dt)
                 FROM
                     w1_activity ac
                 WHERE
                     ac.wo_id = wo.wo_id
             ) AS original_work_dt,
             CASE
                 WHEN bo_status_cd IN (
                     'PLANNING',
                     'PENDAPPROVAL',
                     'APPROVED',
                     'ACTIVE',
                     'REOPENED'
                 ) THEN 1
                 ELSE 0
             END AS open_wo_cnt,
             CASE
                 WHEN bo_status_cd IN (
                     'APPROVED',
                     'ACTIVE'
                 ) THEN 1
                 ELSE 0
             END AS planned_wo_cnt,
             CASE
                 WHEN bo_status_cd = 'PLANNING' THEN 1
                 ELSE 0
             END AS planning_wo_cnt,
             CASE
                 WHEN bo_status_cd = 'ACTIVE'
                      AND required_by_dt < current_date THEN 1
                 ELSE 0
             END AS overdue_wo_cnt
         FROM
             w1_wo wo
         WHERE
              WORK_ROLE_FLG = 'W1PL'
     )
