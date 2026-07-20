CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_BI_WO_VW" ("WO_ID", "BO_STATUS_CD", "BO_STATUS_REASON_CD", "CRE_DTTM", "USER_ID", "DESCR100", "TEMPLATE_NAME", "SVC_HIST_TYPE_CD", "SVC_SCHED_WO_ID", "WORK_REQ_ID", "WORK_PRIORITY_FLG", "DESCRLONG", "PRJ_ID", "REQUESTOR_ID", "W1_CREW_ID", "REQUIRED_BY_DT", "WORK_TYPE_FLG", "MAINT_SCHED_ID", "EMERGENCY_FLG", "WO_NUM", "CONSTR_RELATED_FLG", "WORK_DESIGN_ID", "WORK_CLASS_CD", "WORK_CATEGORY_CD", "OVERHEAD_CD", "PLANNER_CD", "OWNING_ACCESS_GRP_CD", "NODE_ID", "ASSET_ID", "WO_CRE_DTTM", "FINISH_DTTM", "ORIGINAL_WORK_DT", "CONSTR_WO_CNT", "MAINT_WO_CNT", "PM_WO_CNT", "CM_WO_CNT", "ADHERED_PM_DUE_DT_CNT", "ADHERED_CM_DUE_DT_CNT", "CRE_MAINT_WO_CNT", "CMPL_MAINT_WO_CNT", "CRE_CONSTR_WO_CNT", "CMPL_CONSTR_WO_CNT", "OPEN_WO_CNT", "OVERDUE_WO_CNT", "OVERDUE_MAINT_WO_CNT", "OVERDUE_CONSTR_WO_CNT", "OVERDUE_PM_WO_CNT", "OVERDUE_CM_WO_CNT", "OPEN_MAINT_WO_CNT", "OPEN_CONSTR_WO_CNT", "PLANNED_WO_CNT", "PLANNING_WO_CNT", "WO_CNT") DEFAULT COLLATION "USING_NLS_COMP"  AS 
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
     );
