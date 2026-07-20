-- SELECT logic for CISADM.W1_BI_LABORHOURS_VW
SELECT
      timesheet_detail_id,
      w1_ft_id,
      resrc_type_id,
      cost_center_cd,
      cost_category_cd,
      act_id,
      asset_id,
      act_type_cd,
      service_class_cd,
     work_category_cd,
      work_class_cd,
      user_id,
      tmpl_act_id,
      node_id,
      planner_cd,
      wo_id,
      w1_crew_id,
      required_by_dt,
      actvn_dttm,
      work_win_start_dttm,
      work_win_end_dttm,
      owning_access_grp_cd,
      original_work_dt,
      prj_id,
      amt,
      ft_cre_dttm,
      expense_cd,
	  act_resrc_ft_cnt,
      charged_labor_hrs,
      CASE
          WHEN maint_act_cnt = 1
               AND act_charge_type_cnt = 1 THEN charged_labor_hrs
          ELSE 0
      END AS maint_act_labor_hrs,
      CASE
          WHEN cm_act_cnt = 1
               AND act_charge_type_cnt = 1 THEN charged_labor_hrs
          ELSE 0
      END AS cm_act_labor_hrs,
      CASE
          WHEN pm_act_cnt = 1
               AND act_charge_type_cnt = 1 THEN charged_labor_hrs
          ELSE 0
      END AS pm_act_labor_hrs,
      CASE
          WHEN constr_act_cnt = 1
               AND act_charge_type_cnt = 1 THEN charged_labor_hrs
          ELSE 0
      END AS constr_act_labor_hrs,
      CASE
          WHEN regular_ft_cnt = 1 THEN charged_labor_hrs
          ELSE 0
      END AS regular_labor_hrs,
      CASE
          WHEN overtime_cnt = 1 THEN charged_labor_hrs
          ELSE 0
      END AS overtime_labor_hrs,
      CASE
          WHEN regular_ft_cnt = 1
               AND cm_act_cnt = 1 THEN charged_labor_hrs
          ELSE 0
      END AS regular_cm_act_labor_hrs,
      CASE
          WHEN overtime_cnt = 1
               AND cm_act_cnt = 1 THEN charged_labor_hrs
          ELSE 0
      END AS overtime_cm_act_labor_hrs,
      CASE
          WHEN regular_ft_cnt = 1
               AND pm_act_cnt = 1 THEN charged_labor_hrs
          ELSE 0
      END AS regular_pm_act_labor_hrs,
      CASE
          WHEN overtime_cnt = 1
               AND pm_act_cnt = 1 THEN charged_labor_hrs
          ELSE 0
      END AS overtime_pm_act_labor_hrs,
      CASE
          WHEN regular_ft_cnt = 1
               AND constr_act_cnt = 1 THEN charged_labor_hrs
          ELSE 0
      END AS regular_constr_act_labor_hrs,
      CASE
          WHEN overtime_cnt = 1
               AND constr_act_cnt = 1 THEN charged_labor_hrs
          ELSE 0
      END AS overtime_constr_act_labor_hrs,
      CASE
          WHEN emergency_flg = 'W1YS' THEN charged_labor_hrs
          ELSE 0
      END AS emergency_labor_hrs,
      CASE
          WHEN regular_ft_cnt = 1
               AND emergency_flg = 'W1YS' THEN charged_labor_hrs
          ELSE 0
      END AS regular_emergency_labor_hrs,
      CASE
          WHEN overtime_cnt = 1
               AND emergency_flg = 'W1YS' THEN charged_labor_hrs
          ELSE 0
      END AS overtime_emergency_labor_hrs
  FROM
      (
          SELECT
              ac.act_id,
              td.resrc_type_id,
              ac.user_id,
              ac.tmpl_act_id,
              ac.node_id,
              aa.asset_id,
              ac.act_type_cd,
              ac.service_class_cd,
             ac.work_category_cd,
              ac.work_class_cd,
              ac.planner_cd,
              ac.wo_id,
              ac.emergency_flg,
              ac.w1_crew_id,
              ac.required_by_dt,
              ac.actvn_dttm,
              ac.work_win_start_dttm,
              ac.work_win_end_dttm,
              ac.owning_access_grp_cd,
              ac.original_work_dt,
              td.prj_id,
              ft.w1_ft_id,
              ft.timesheet_detail_id,
              CASE
                  WHEN aa.act_id IS NOT NULL THEN ( ft.amt * aa.percentage ) / 100
                  ELSE ft.amt
              END AS amt,
              ft.ft_cre_dttm,
              td.expense_cd,
             CASE
                  WHEN aa.act_id IS NOT NULL THEN ( td.hours * aa.percentage * tc.percentage ) / 10000
                  ELSE ( td.hours * tc.percentage ) / 100
              END AS charged_labor_hrs,
              ft.cost_category_cd,
              ft.cost_center_cd,
			  1 AS ACT_RESRC_FT_CNT, 
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
                  WHEN td.reg_overtime_flg = 'W1RE' THEN 1
                  ELSE 0
              END AS regular_ft_cnt,
              CASE
                  WHEN td.reg_overtime_flg = 'W1OT' THEN 1
                  ELSE 0
              END AS overtime_cnt,
              CASE
                  WHEN td.charge_type_flg = 'W1AC' THEN 1
                  ELSE 0
              END AS act_charge_type_cnt
          FROM
              w1_timesheet_detail td
              JOIN (
                  SELECT
                      ft.timesheet_detail_id,
                      ft.w1_ft_id,
                      ft.w1_ft_type_flg,
                      ft.act_id,
                      gl.cost_center_cd,
                      ec.cost_category_cd,
                      ft.cre_dttm   AS ft_cre_dttm,
                      SUM(gl.amt) amt
                  FROM
                      w1_ft ft,
                      w1_ft_gl_dtl gl,
                      w1_expense_cd ec
                  WHERE
                      ft.sibling_cancelled_flg = 'W1NO'
                      AND gl.w1_ft_id = ft.w1_ft_id
                      AND ( gl.amt * ft.amt ) * nvl2(nvl(ft.rtn_line_id,ft.mat_ret_line_id),-1,1) > 0
                      AND ft.bo_status_cd = 'FROZEN'
                      AND ec.expense_cd = gl.expense_cd
                  GROUP BY
                      ft.timesheet_detail_id,
                      ft.w1_ft_id,
                      ft.w1_ft_type_flg,
                      ft.act_id,
                      gl.cost_center_cd,
                      ec.cost_category_cd,
                      ft.cre_dttm
              ) ft ON ft.timesheet_detail_id = td.timesheet_detail_id
              JOIN w1_resrc_type rt ON rt.resrc_type_id = td.resrc_type_id
                                       AND rt.w1_resrc_class_flg = 'W1CR'
 
             JOIN w1_timsheetdtl_cost_ctr tc ON tc.timesheet_detail_id = td.timesheet_detail_id
                                                 AND tc.cost_center_cd = ft.cost_center_cd
              LEFT OUTER JOIN w1_activity ac ON ac.act_id = ft.act_id
                                                AND NOT ac.bo_status_cd IN (
                  'CANCELED'
              )
              LEFT OUTER JOIN w1_activity_type act ON act.act_type_cd = ac.act_type_cd
                                                      AND act.track_cost_flg = 'W1YS'
              LEFT OUTER JOIN w1_activity_asset aa ON aa.act_id = ac.act_id
                                                      AND aa.participation_flg = 'W1AW'
              LEFT OUTER JOIN w1_wo wo ON wo.wo_id = ac.wo_id
          WHERE
              NOT td.bo_status_cd IN (
                  'CANCELLED'
              )
      )
