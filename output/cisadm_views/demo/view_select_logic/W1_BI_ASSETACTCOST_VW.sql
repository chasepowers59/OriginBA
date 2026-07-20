-- SELECT logic for CISADM.W1_BI_ASSETACTCOST_VW
SELECT
      act_id,
      asset_id,
      w1_ft_id,
      w1_resrc_class_flg,
      cost_category_cd,
      wo_id,
      node_id,
      act_cre_dttm,
      renewal_flg,
      maintenance_cost,
      renewal_cost,
      w1_bi_total_cost,
      failure_repair_cost,
      failure_count,
      acquisition_dt,
      in_service_dt,
      predctd_wear_out_dt,
      w1_crew_id,
      finish_dttm,
      asset_act_count,
      actvn_dttm,
      original_work_dt,
      required_by_dt,
      work_win_start_dttm,
      work_win_end_dttm,
      ft_cre_dttm,
      expense_cd,
	  cost_center_cd,
      prj_id,
      planner_cd,
      tmpl_act_id,
      owning_access_grp_cd,
      user_id,
      work_class_cd,
      work_category_cd,
      act_type_cd,
      service_class_cd,
      CASE
          WHEN labor_cnt = 1 THEN 
              maintenance_cost
          ELSE 
              0
      END AS maintenance_labor_cost,
      CASE
          WHEN material_cnt = 1 THEN 
               maintenance_cost
          ELSE 
               0
      END AS maintenance_matl_cost,
      CASE
          WHEN equipment_cnt = 1 THEN 
               maintenance_cost
          ELSE
                0
      END AS maintenance_equip_cost,
      CASE
          WHEN odc_cnt = 1 THEN 
              maintenance_cost
          ELSE 
              0
      END AS maintenance_odc_cost,
      CASE
          WHEN cm_act_cnt = 1 THEN 
               maintenance_cost
          ELSE
                0
      END AS maintenance_cm_cost,
      CASE
          WHEN cm_act_cnt = 1
               AND labor_cnt = 1 THEN 
            maintenance_cost
          ELSE
             0
      END AS maintenance_cm_labor_cost,
      CASE
          WHEN cm_act_cnt = 1
               AND material_cnt = 1 THEN
             maintenance_cost
          ELSE 
            0
      END AS maintenance_cm_matl_cost,
      CASE
          WHEN cm_act_cnt = 1
               AND equipment_cnt = 1 THEN 
               maintenance_cost
          ELSE 
               0
      END AS maintenance_cm_equip_cost,
      CASE
          WHEN cm_act_cnt = 1
               AND odc_cnt = 1 THEN
                 maintenance_cost
          ELSE 
              0
      END AS maintenance_cm_odc_cost,
      CASE
          WHEN pm_act_cnt = 1 THEN 
               maintenance_cost
          ELSE 
               0
      END AS maintenance_pm_cost,
      CASE
          WHEN pm_act_cnt = 1
               AND labor_cnt = 1 THEN 
                maintenance_cost
          ELSE 
               0
      END AS maintenance_pm_labor_cost,
      CASE
          WHEN pm_act_cnt = 1
               AND material_cnt = 1 THEN 
               maintenance_cost
          ELSE 
               0
      END AS maintenance_pm_matl_cost,
      CASE
          WHEN pm_act_cnt = 1
               AND equipment_cnt = 1 THEN 
              maintenance_cost
          ELSE 
              0
      END AS maintenance_pm_equip_cost,
      CASE
          WHEN pm_act_cnt = 1
               AND odc_cnt = 1 THEN 
               maintenance_cost
          ELSE 
            0
      END AS maintenance_pm_odc_cost,
      CASE
          WHEN emergency_flg = 'W1YS' THEN
            maintenance_cost
          ELSE
            0
      END AS maintenance_em_cost,
      CASE
          WHEN emergency_flg = 'W1YS'
               AND labor_cnt = 1 THEN 
            maintenance_cost
          ELSE 
            0
      END AS maintenance_em_labor_cost,
      CASE
          WHEN emergency_flg = 'W1YS'
               AND material_cnt = 1 THEN
              maintenance_cost
          ELSE 
              0
      END AS maintenance_em_matl_cost,
      CASE
          WHEN emergency_flg = 'W1YS'
               AND equipment_cnt = 1 THEN 
              maintenance_cost
          ELSE 
              0
      END AS maintenance_em_equip_cost,
      CASE
          WHEN emergency_flg = 'W1YS'
               AND odc_cnt = 1 THEN
            maintenance_cost
          ELSE
           0
      END AS maintenance_em_odc_cost,
      total_est_cost,
      CASE
          WHEN labor_cnt = 1 THEN 
               total_est_cost
          ELSE
              0
      END AS est_labor_cost,
      CASE
          WHEN material_cnt = 1 THEN 
               total_est_cost
          ELSE 
              0
      END AS est_material_cost,
      CASE
          WHEN equipment_cnt = 1 THEN 
          total_est_cost
          ELSE 
         0
      END AS est_equipment_cost,
      CASE
        WHEN odc_cnt = 1 THEN
            total_est_cost
        ELSE
            0
      END AS est_odc_cost,
      CASE
        WHEN planned_act_cnt = 1 THEN
            total_est_cost
        ELSE
            0
      END AS planned_est_cost,
      CASE
          WHEN planned_act_cnt = 1
             AND labor_cnt = 1 THEN
            total_est_cost
        ELSE
            0
      END AS planned_est_labor_cost,
     CASE
          WHEN planned_act_cnt = 1
             AND material_cnt = 1 THEN
            total_est_cost
        ELSE
            0
      END AS planned_est_matl_cost,
      CASE
          WHEN planned_act_cnt = 1
             AND equipment_cnt = 1 THEN
            total_est_cost
        ELSE
            0
      END AS planned_est_equip_cost,
      CASE
          WHEN planned_act_cnt = 1
             AND odc_cnt = 1 THEN
            total_est_cost
        ELSE
            0
      END AS planned_est_odc_cost,
      CASE
        WHEN completed_act_cnt = 1 THEN
            total_est_cost
        ELSE
            0
      END AS compl_est_cost,
      CASE
          WHEN completed_act_cnt = 1
             AND labor_cnt = 1 THEN
            total_est_cost
        ELSE
            0
      END AS compl_est_labor_cost,
      CASE
          WHEN completed_act_cnt = 1
             AND material_cnt = 1 THEN
            total_est_cost
        ELSE
            0
      END AS compl_est_matl_cost,
      CASE
          WHEN completed_act_cnt = 1
             AND equipment_cnt = 1 THEN
            total_est_cost
        ELSE
            0
      END AS compl_est_equip_cost,
      CASE
          WHEN completed_act_cnt = 1
             AND odc_cnt = 1 THEN
            total_est_cost
        ELSE
            0
      END AS compl_est_odc_cost,
      CASE
        WHEN completed_act_cnt = 1 THEN
            w1_bi_total_cost
        ELSE
            0
      END AS compl_actual_cost,
      CASE
          WHEN completed_act_cnt = 1
             AND labor_cnt = 1 THEN
            w1_bi_total_cost
        ELSE
            0
      END AS compl_actual_labor_cost,
      CASE
          WHEN completed_act_cnt = 1
             AND material_cnt = 1 THEN
            w1_bi_total_cost
        ELSE
            0
      END AS compl_actual_matl_cost,
      CASE
          WHEN completed_act_cnt = 1
             AND equipment_cnt = 1 THEN
            w1_bi_total_cost
        ELSE
            0
      END AS compl_actual_equip_cost,
      CASE
          WHEN completed_act_cnt = 1
             AND odc_cnt = 1 THEN
            w1_bi_total_cost
        ELSE
            0
      END AS compl_actual_odc_cost,
      CASE
        WHEN open_act_cnt = 1 THEN
            w1_bi_total_cost
        ELSE
            0
      END AS open_actual_cost,
      CASE
          WHEN open_act_cnt = 1
             AND labor_cnt = 1 THEN
            w1_bi_total_cost
        ELSE
            0
      END AS open_actual_labor_cost,
      CASE
          WHEN open_act_cnt = 1
             AND material_cnt = 1 THEN
            w1_bi_total_cost
        ELSE
            0
      END AS open_actual_matl_cost,
      CASE
          WHEN open_act_cnt = 1
             AND equipment_cnt = 1 THEN
            w1_bi_total_cost
        ELSE
            0
      END AS open_actual_equip_cost,
      CASE
          WHEN open_act_cnt = 1
             AND odc_cnt = 1 THEN
            w1_bi_total_cost
        ELSE
            0
      END AS open_actual_odc_cost
  FROM
      (
          SELECT
              act_id,
              asset_id,
              w1_ft_id,
              w1_resrc_class_flg,
              wo_id,
              node_id,
              act_cre_dttm,
              renewal_flg,
              failure_repair_cost,
              failure_count,
              acquisition_dt,
              in_service_dt,
              predctd_wear_out_dt,
              w1_crew_id,
              finish_dttm,
              --asset_act_count,
              actvn_dttm,
              original_work_dt,
              required_by_dt,
              work_win_start_dttm,
              work_win_end_dttm,
              maintenance_cost,
              renewal_cost,
              w1_bi_total_cost,
              ft_cre_dttm,
              expense_cd,
			  cost_center_cd,
              prj_id,
              planner_cd,
              tmpl_act_id,
              owning_access_grp_cd,
              user_id,
              work_class_cd,
              work_category_cd,
              act_type_cd,
              service_class_cd,
            1 AS asset_act_count,
              CASE
                WHEN w1_resrc_class_flg = 'W1CR' THEN
                    1
                ELSE
                    0
              END AS labor_cnt,
              CASE
                WHEN w1_resrc_class_flg = 'W1MT' THEN
                    1
                ELSE
                    0
              END AS material_cnt,
              CASE
                WHEN w1_resrc_class_flg = 'W1EQ' THEN
                    1
                ELSE
                    0
              END AS equipment_cnt,
              CASE
                WHEN w1_resrc_class_flg = 'W1OT' THEN
                    1
                ELSE
                    0
              END AS odc_cnt,
              cost_category_cd,
            ( total_est_cost * a.percentage * a.costcenterpercentage ) / 10000 AS total_est_cost,
              completed_act_cnt,
              planned_act_cnt,
              open_act_cnt,
              pm_act_cnt,
              cm_act_cnt,
              emergency_flg
          FROM
              (
                  SELECT
                    act.act_id                AS act_id,
                      actal.asset_id            AS asset_id,
                    cost.w1_ft_id             AS w1_ft_id,
                    cost.w1_resrc_class_flg   AS w1_resrc_class_flg,
                      act.wo_id                 AS wo_id,
                      actal.node_id             AS node_id,
                      act.cre_dttm              AS act_cre_dttm,
                      sc.renewal_flg            AS renewal_flg,
                      actal.percentage,
                    acc.percentage            AS costcenterpercentage,
                    cost.amount               AS amount,
                    cost.total_est_cost       AS total_est_cost,
                      CASE
                        WHEN sc.renewal_flg = 'W1NO' THEN
                            ( cost.amount * actal.percentage / 100 )
                        ELSE
                            0
                      END maintenance_cost,
                      CASE
                        WHEN sc.renewal_flg = 'W1YS' THEN
                            ( cost.amount * actal.percentage / 100 )
                        ELSE
                            0
                      END renewal_cost,
                    ( cost.amount * actal.percentage / 100 ) AS w1_bi_total_cost,
                      CASE
                        WHEN actal.shcount > 0 THEN
                            ( cost.amount * actal.percentage / 100 )
                        ELSE
                            0
                      END failure_repair_cost,
                      CASE
                          WHEN wo.wo_id IS NOT NULL
                             AND wo.work_type_flg = 'W1PM' THEN
                            1
                        ELSE
                            0
                      END AS pm_act_cnt,
                      CASE
                          WHEN wo.wo_id IS NOT NULL
                             AND wo.work_type_flg = 'W1RG' THEN
                            1
                        ELSE
                            0
                      END AS cm_act_cnt,
                      CASE
                          WHEN act.bo_status_cd IN (
                              'COMPLETE'
                              ,'CLOSED'
                        ) THEN
                            1
                        ELSE
                            0
                      END AS completed_act_cnt,
                      CASE
                          WHEN act.bo_status_cd IN (
                              'APPROVED',
                              'ACTIVE'
                        ) THEN
                            1
                        ELSE
                            0
                      END AS planned_act_cnt,
                      CASE
                          WHEN NOT ( act.bo_status_cd IN (
                              'COMPLETE'
                              ,'CLOSED'
                        ) ) THEN
                            1
                        ELSE
                            0
                      END AS open_act_cnt,
                      act.emergency_flg,
                       actal.shcount * acc.percentage / 100  AS failure_count,
                      --actal.shcount             AS failure_count,
                      ast.acquisition_dt        AS acquisition_dt,
                      trunc(ast.in_service_dt) AS in_service_dt,
                      ast.predctd_wear_out_dt   AS predctd_wear_out_dt,
                      1 AS asset_act_count,
                      act.w1_crew_id            AS w1_crew_id,
                    decode(TRIM(wo.bo_status_cd), 'COMPLETED', wo.status_upd_dttm,(
                          SELECT
                              MAX(lg.log_dttm)
                          FROM
                              w1_wo_log lg
                          WHERE
                             lg.wo_id = wo.wo_id
                              AND lg.bo_status_cd = 'COMPLETED'
                      ) ) AS finish_dttm,
                      act.actvn_dttm,
                      act.original_work_dt,
                      act.required_by_dt,
                      act.work_win_start_dttm,
                      act.work_win_end_dttm,
                    cost.cost_category_cd,
                    cost.ft_cre_dttm,
                    cost.expense_cd,
                    cost.cost_center_cd,
                      act.prj_id,
                      act.planner_cd,
                      act.tmpl_act_id,
                      act.owning_access_grp_cd,
                      act.user_id,
                      act.work_class_cd,
                      act.work_category_cd,
                      act.act_type_cd,     
                      act.service_class_cd
                  FROM
                      w1_activity act
                      JOIN (
                         SELECT
                              z.act_id,
                              z.asset_id,
                              node_id,
                              z.percentage,
                              z.participation_flg,
                              (
                                  SELECT
                                      COUNT(*)
                                  FROM
                                      w1_svc_hist sh,
                                      w1_svc_hist_type sht
                                  WHERE
                                      sht.svc_hist_type_cd = sh.svc_hist_type_cd
                                      AND sht.svc_hist_category_flg = 'W1FA'
                                      AND sh.act_id = z.act_id
                                      AND sh.asset_id = z.asset_id
                              ) AS shcount
                          FROM
                              w1_activity_asset z
                          WHERE
                              z.participation_flg = 'W1AW'
                      ) actal ON actal.act_id = act.act_id
                      JOIN w1_service_class sc ON sc.service_class_cd = act.service_class_cd
                                                  AND sc.renewal_flg IN (
                          'W1NO',
                          'W1YS'
                      )
                      JOIN w1_asset ast ON ast.asset_id = actal.asset_id
                      JOIN w1_wo wo ON wo.wo_id = act.wo_id
                      JOIN (
                          SELECT
                            act_id,
                            w1_ft_id,
                            w1_resrc_class_flg,
                            amount,
                            CASE
                                WHEN amount <= 0 THEN
                                    0
                                ELSE
                                    (
                                        SELECT
                                            nvl(SUM(round(arr.orig_estimate / resrcreqmtcount,2)),0)
                                        FROM
                                            w1_act_resrc_reqmt arr
                                        WHERE
                                            arr.act_resrc_reqmt_id = ft2.act_resrc_reqmt_id
                                    )
                            END AS total_est_cost,
                            cost_category_cd,
                            ft_cre_dttm,
                            expense_cd,
                            cost_center_cd
                        FROM
                            (
                                SELECT
                                    ft.act_id     AS act_id,
                                    ft.w1_ft_id   AS w1_ft_id,
                                    CASE
                                        WHEN ft.timesheet_detail_id IS NOT NULL THEN
                                            'W1CR'
                                        WHEN ft.mat_iss_line_id IS NOT NULL
                                             OR ft.mat_ret_line_id IS NOT NULL THEN
                                            'W1MT'
                                        WHEN ft.odc_dtl_id IS NOT NULL THEN
                                            (
                                                SELECT
                                                    w1_resrc_class_flg
                                                FROM
                                                    w1_odc_dtl      odc,
                                                    w1_resrc_type   rt
                                                WHERE
                                                    odc.odc_dtl_id = ft.odc_dtl_id
                                                    AND rt.resrc_type_id = odc.resrc_type_id
                                            )
                                        WHEN ft.acpt_line_id IS NOT NULL THEN
                                            nvl2((
                                                SELECT
                                                    stock_item_dtl_id
                                                FROM
                                                    w1_acpt_line al
                                                WHERE
                                                    al.acpt_line_id = ft.acpt_line_id
                                            ), 'W1MT',(
                                                SELECT
                                                    w1_resrc_class_flg
                                                FROM
                                                    w1_acpt_line    al, w1_resrc_type   rt
                                                WHERE
                                                    al.acpt_line_id = ft.acpt_line_id
                                                    AND rt.resrc_type_id = al.resrc_type_id
                                            ))
                                        WHEN ft.rtn_line_id IS NOT NULL THEN
                                            nvl2((
                                                SELECT
                                                    trim(stock_item_dtl_id)
                                                FROM
                                                    w1_rtn_line rl
                                                WHERE
                                                    rl.rtn_line_id = ft.rtn_line_id
                                            ), 'W1MT',(
                                                SELECT
                                                    w1_resrc_class_flg
                                                FROM
                                                    w1_rtn_line     rl, w1_resrc_type   rt, w1_po_line      pl
                                                WHERE
                                                    rl.rtn_line_id = ft.rtn_line_id
                                                    AND pl.po_line_id = rl.po_line_id
                                                    AND rt.resrc_type_id = pl.resrc_type_id
                                            ))
                                        WHEN ft.invoice_line_id IS NOT NULL THEN
                                            (
                                                SELECT
                                                    w1_resrc_class_flg
                                                FROM
                                                    w1_invoice_line   il,
                                                    w1_resrc_type     rt
                                                WHERE
                                                    il.invoice_line_id = ft.invoice_line_id
                                                    AND rt.resrc_type_id = il.resrc_type_id
                                            )
                                        ELSE
                                            NULL
                                    END AS w1_resrc_class_flg,
                                    CASE
                                        WHEN ft.timesheet_detail_id IS NOT NULL THEN
                                            (
                                                SELECT
                                                    t.act_resrc_reqmt_id
                                                FROM
                                                    w1_timesheet_detail t
                                                WHERE
                                                    t.timesheet_detail_id = ft.timesheet_detail_id
                                            )
                                        WHEN ft.rtn_line_id IS NOT NULL THEN
                                            (
                                                SELECT
                                                    p.act_resrc_reqmt_id
                                                FROM
                                                    w1_rtn_line   rl,
                                                    w1_po_line    p
                                                WHERE
                                                    rl.rtn_line_id = ft.rtn_line_id
                                                    AND p.po_line_id = rl.po_line_id
                                            )
                                        WHEN ft.mat_iss_line_id IS NOT NULL THEN
                                            (
                                                SELECT
                                                    m.act_resrc_reqmt_id
                                                FROM
                                                    w1_mat_req_line   m,
                                                    w1_mat_iss_line   n
                                                WHERE
                                                    n.mat_iss_line_id = ft.mat_iss_line_id
                                                    AND m.mat_req_line_id = n.mat_req_line_id
                                            )
                                        WHEN ft.mat_ret_line_id IS NOT NULL THEN
                                            (
                                                SELECT
                                                    m.act_resrc_reqmt_id
                                                FROM
                                                    w1_mat_req_line   m,
                                                    w1_mat_iss_line   n,
                                                    w1_mat_ret_line   l
                                                WHERE
                                                    l.mat_ret_line_id = ft.mat_ret_line_id
                                                    AND n.mat_iss_line_id = l.mat_iss_line_id
                                                    AND m.mat_req_line_id = n.mat_req_line_id
                                            )
                                        WHEN ft.odc_dtl_id IS NOT NULL THEN
                                            (
                                                SELECT
                                                    o.act_resrc_reqmt_id
                                                FROM
                                                    w1_odc_dtl o
                                                WHERE
                                                    o.odc_dtl_id = ft.odc_dtl_id
                                            )
                                        WHEN ft.acpt_line_id IS NOT NULL THEN
                                            (
                                                SELECT
                                                    p.act_resrc_reqmt_id
                                                FROM
                                                    w1_po_line     p,
                                                    w1_rcpt_line   r,
                                                    w1_acpt_line   l
                                                WHERE
                                                    l.acpt_line_id = ft.acpt_line_id
                                                    AND r.rcpt_line_id = l.rcpt_line_id
                                                    AND p.po_line_id = r.po_line_id
                                            )
                                        WHEN ft.invoice_line_id IS NOT NULL THEN
                                            (
                                                SELECT
                                                    p.act_resrc_reqmt_id
                                                FROM
                                                    w1_po_line        p,
                                                    w1_invoice_line   i
                                                WHERE
                                                    i.invoice_line_id = ft.invoice_line_id
                                                    AND p.po_line_id = i.po_line_id
                                            )
                                        ELSE
                                            NULL
                                    END AS act_resrc_reqmt_id,
                                    CASE
                                        WHEN ft.timesheet_detail_id IS NOT NULL THEN
                                            (
                                                SELECT
                                                    COUNT(*)
                                                FROM
                                                    w1_timesheet_detail dt
                                                WHERE
                                                    dt.act_resrc_reqmt_id = (
                                                        SELECT
                                                            ftdt.act_resrc_reqmt_id
                                                        FROM
                                                            w1_timesheet_detail ftdt
                                                        WHERE
                                                            ftdt.timesheet_detail_id = ft.timesheet_detail_id
                                                    )
                                            )
                                          WHEN ft.mat_iss_line_id IS NOT NULL THEN
                                              (
                                                 SELECT count(*)  FROM
                                                  w1_mat_req_line   dm1
                                                WHERE
                                                  dm1.act_resrc_reqmt_id = (
                                                SELECT 
                                                  dm.act_resrc_reqmt_id
                                                FROM
                                                  w1_mat_req_line   dm,
                                                  w1_mat_iss_line   dn
                                                WHERE
                                                  dn.mat_iss_line_id = ft.mat_iss_line_id
                                                  AND dm.mat_req_line_id = dn.mat_req_line_id
                                                  )
                                              )                                                    
                                      WHEN ft.odc_dtl_id IS NOT NULL THEN
                                            (
                                              select count(*) from w1_odc_dtl od1 
                                              where od1.act_resrc_reqmt_id=(
                                                SELECT
                                                    od.act_resrc_reqmt_id
                                                FROM
                                                    w1_odc_dtl od
                                                WHERE
                                                    od.odc_dtl_id = ft.odc_dtl_id)
                                            )
                                    
                                                                         
                                         WHEN ft.acpt_line_id IS NOT NULL THEN
                                            (
                                               select count(*) from w1_po_line dpp
                                               where dpp.act_resrc_reqmt_id = (
                                                
                                                SELECT
                                                    dp.act_resrc_reqmt_id
                                                FROM
                                                    w1_po_line     dp,
                                                    w1_rcpt_line   dr,
                                                    w1_acpt_line   dl
                                                WHERE
                                                    dl.acpt_line_id = ft.acpt_line_id
                                                    AND dr.rcpt_line_id = dl.rcpt_line_id
                                                    AND dp.po_line_id = dr.po_line_id
                                                    )
                                            )
                                        WHEN ft.invoice_line_id IS NOT NULL THEN
                                            (
                                               select count(*) from w1_po_line dpi 
                                               where dpi.act_resrc_reqmt_id = 
                                               ( SELECT
                                                    dp.act_resrc_reqmt_id
                                                FROM
                                                    w1_po_line        dp,
                                                    w1_invoice_line   di
                                                WHERE
                                                    di.invoice_line_id = ft.invoice_line_id
                                                    AND dp.po_line_id = di.po_line_id)
                                            )  
                                            
                                        ELSE
                                            1
                                    END AS resrcreqmtcount,
                                    amount        AS amount,
                                    ft.cost_category_cd,
                                    ft.ft_cre_dttm,
                                    ft.expense_cd,
                                    ft.cost_center_cd
                                FROM
                                    (
                                        SELECT
                              ft.w1_ft_id,
                              ft.act_id,
                              ft.timesheet_detail_id,
                              ft.odc_dtl_id,
                              ft.mat_iss_line_id,
                             ft.mat_ret_line_id,
                              ft.acpt_line_id,
                              ft.rtn_line_id,
                              ft.invoice_line_id,
                               ec.cost_category_cd,
                              ft.cre_dttm   AS ft_cre_dttm,
                              gl.expense_cd,
							  gl.cost_center_cd,
                              SUM(gl.amt) amount
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
                             ft.w1_ft_id,
                              ft.act_id,
                              ft.timesheet_detail_id,
                              ft.odc_dtl_id,
                              ft.mat_iss_line_id,
                              ft.mat_ret_line_id,
                              ft.acpt_line_id,
                              ft.rtn_line_id,
                              ft.invoice_line_id,
                              ec.cost_category_cd,
                              ft.cre_dttm,
                              gl.expense_cd,
                              gl.cost_center_cd
                                    ) ft
                            ) ft2
                        UNION
                        ( SELECT
                            arr.act_id          AS act_id,
                            NULL AS w1_ft_id,
                            arr.w1_resrc_class_flg,
                            0 AS amount,
                            arr.orig_estimate   AS orig_estimate,
                            arr.cost_category_cd,
                            NULL AS ft_cre_dttm,
                            arr.expense_cd,
                            arr.cost_center_cd
                        FROM
                            (
                                SELECT
                                    ar.act_id,
                                    ec.cost_category_cd,
                                    ar.expense_cd,
                                    rt.w1_resrc_class_flg,
                                    acc.cost_center_cd,
                                    SUM(ar.orig_estimate) AS orig_estimate
                                FROM
                                    w1_act_resrc_reqmt        ar,
                                    w1_expense_cd             ec,
                                    w1_resrc_type             rt,
                                    w1_activity               act,
                                    w1_activity_cost_center   acc
                                WHERE
                                    ar.act_id = act.act_id
                                    AND act.bo_status_cd <> 'CANCELED'
                                    AND ec.expense_cd = ar.expense_cd
                                    AND ar.bo_status_cd <> 'CANCELED'
                                    AND acc.act_id = act.act_id
                                    AND rt.resrc_type_id = decode(ar.stock_item_dtl_id, NULL, ar.resrc_type_id,(
                                        SELECT
                                            sid.resrc_type_id
                                        FROM
                                            w1_stock_item_dtl sid
                                        WHERE
                                            sid.stock_item_dtl_id = ar.stock_item_dtl_id
                                    ))
                                    AND NOT EXISTS (
                                        SELECT
                                            'x'
                                        FROM
                                            w1_timesheet_detail t
                                        WHERE
                                            t.act_resrc_reqmt_id = ar.act_resrc_reqmt_id
                                            and   t.bo_status_cd in ('POSTED')
                                    )
                                    AND NOT EXISTS (
                                        SELECT
                                            'x'
                                        FROM
                                            w1_po_line p
                                        WHERE
                                            p.act_resrc_reqmt_id = ar.act_resrc_reqmt_id
                                            and p.bo_status_cd  in ('ISSUED','CLOSED')
                                    )
                                    AND NOT EXISTS (
                                        SELECT
                                            'x'
                                        FROM
                                            w1_mat_req_line m
                                        WHERE
                                            m.act_resrc_reqmt_id = ar.act_resrc_reqmt_id
                                             and  m.bo_status_cd  in ('ISSUED')
                                    )
                                    AND NOT EXISTS (
                                        SELECT
                                            'x'
                                        FROM
                                            w1_odc_dtl o
                                        WHERE
                                            o.act_resrc_reqmt_id = ar.act_resrc_reqmt_id
                                             and  o.bo_status_cd  in ('POSTED')
                                    )
                                GROUP BY
                                    ar.act_id,
                                    ec.cost_category_cd,
                                    rt.w1_resrc_class_flg,
                                    ar.expense_cd,
                                    acc.cost_center_cd
                            ) arr
                        )
                    ) cost ON cost.act_id = act.act_id
                    JOIN w1_activity_cost_center   acc ON act.act_id = acc.act_id
                                                        AND acc.cost_center_cd = cost.cost_center_cd
             ) a
      )
