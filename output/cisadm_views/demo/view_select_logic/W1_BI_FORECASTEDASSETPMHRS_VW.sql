-- SELECT logic for CISADM.W1_BI_FORECASTEDASSETPMHRS_VW
with assetFcst as
(     SELECT
          fc.asset_id,
          fc.maint_trigger_id,
          MIN(fc.forecast_dt) AS next_maint_dt
      FROM
          w1_asset_maint_trigger_fcst fc
      WHERE
          fc.forecast_dt >= current_date
      GROUP BY
          fc.asset_id,
          fc.maint_trigger_id  )
  SELECT
      asset_id              as ASSET_ID,
      resrc_type_id         as RESRC_TYPE_ID,
      node_id               as NODE_ID,
      in_service_dt         as IN_SERVICE_DT,
      predctd_wear_out_dt   as PREDCTD_WEAR_OUT_DT,
      acquisition_dt        as ACQUISITION_DT,
      SUM(labor_hours_next_yr) as LABOR_HRS_NEXT_YR,
      SUM(labor_hours_next_2yrs) as LABOR_HRS_NEXT_2_YRS,
      SUM(labor_hours_next_5yrs) as LABOR_HRS_NEXT_5_YRS,
      SUM(labor_hours_next_10yrs) as LABOR_HRS_NEXT_10_YRS,
      SUM(labor_hours_remain_life) as LABOR_HRS_REMAIN_LIFE,
      remain_life_yrs as REMAIN_LIFE_YRS,
      owning_access_grp_cd as OWNING_ACCESS_GRP_CD,
      1 as ASSET_RESRC_TYPE_CNT
  FROM
      (
          SELECT
              ast.asset_id,
              wo_hours.resrc_type_id,
              trg.node_id,
              trg.tmpl_wo_id,
              trunc(ast.in_service_dt) AS in_service_dt,
              trunc(ast.predctd_wear_out_dt) as predctd_wear_out_dt,
              trunc(ast.acquisition_dt) as acquisition_dt,
              trg.days_bet_pm,
              trg.next_maint_dt,
              wo_hours.tot_labor_hours,
              wo_hours.tot_labor_hours * asset_percentage * num_triggers_next_yr AS labor_hours_next_yr,
              wo_hours.tot_labor_hours * asset_percentage * num_triggers_next_2yrs AS labor_hours_next_2yrs,
              wo_hours.tot_labor_hours * asset_percentage * num_triggers_next_5yrs AS labor_hours_next_5yrs,
              wo_hours.tot_labor_hours * asset_percentage * num_triggers_next_10yrs AS labor_hours_next_10yrs,
             CASE
                 WHEN trg.months_bet_pm > 0 THEN wo_hours.tot_labor_hours * asset_percentage * floor( (nvl2(trunc(ast.in_service_dt),round
                 (greatest( (coalesce(ast.useful_life,aty.useful_life,0) * 12) - months_between(current_date,trunc(ast.in_service_dt
                 ) ),0),1),0) ) / trg.months_bet_pm)
                 ELSE wo_hours.tot_labor_hours * asset_percentage * floor( (nvl2(trunc(ast.in_service_dt),round(greatest( (coalesce(ast.useful_life,aty.useful_life,0) * 365) - (current_date - trunc(ast.in_service_dt) ),0),1),0) ) / trg.days_bet_pm
                 )
             END AS labor_hours_remain_life,
             nvl2(trunc(ast.in_service_dt),round(greatest( (coalesce(ast.useful_life,aty.useful_life,0) * 365) - (current_date - trunc
             (ast.in_service_dt) ),0) / 365,1),0) AS remain_life_yrs,
             ast.owning_access_grp_cd
          FROM
              (
                  SELECT
                      asset_id,
                      maint_trigger_id,
                      node_id,
                      tmpl_wo_id,
                      tmpl_act_id,
                      next_maint_dt,
                      months_bet_pm,
                      days_bet_pm,
                      CASE
                          WHEN months_bet_pm > 0 THEN floor( ( (months_between(add_months(current_date,12),next_maint_dt) ) ) / months_bet_pm
                          ) + 1
                          ELSE floor( ( (add_months(current_date,12) - next_maint_dt) ) / days_bet_pm) + 1
                      END AS num_triggers_next_yr,
                      CASE
                          WHEN months_bet_pm > 0 THEN floor( ( (months_between(add_months(current_date,24),next_maint_dt) ) ) / months_bet_pm
                          ) + 1
                          ELSE floor( ( (add_months(current_date,24) - next_maint_dt) ) / days_bet_pm) + 1
                      END AS num_triggers_next_2yrs,
                      CASE
                          WHEN months_bet_pm > 0 THEN floor( ( (months_between(add_months(current_date,60),next_maint_dt) ) ) / months_bet_pm
                          ) + 1
                          ELSE floor( ( (add_months(current_date,60) - next_maint_dt) ) / days_bet_pm) + 1
                      END AS num_triggers_next_5yrs,
                      CASE
                          WHEN months_bet_pm > 0 THEN floor( ( (months_between(add_months(current_date,120),next_maint_dt) ) ) / months_bet_pm
                          ) + 1
                          ELSE floor( ( (add_months(current_date,120) - next_maint_dt) ) / days_bet_pm) + 1
                      END AS num_triggers_next_10yrs,
                      asset_percentage
                  FROM
                      (
                          SELECT
                              f.asset_id,
                              f.maint_trigger_id,
                              nvl(an2.curr_node_id, (
                                  select
                                      z.curr_node_id
                                  from
                                      w1_asset_node z
                                  where
                                      an2.curr_attch_to_asset_id = z.curr_asset_id
                              ) ) as node_id,
                              mt.tmpl_wo_id,
                              ta.tmpl_act_id,
                              next_maint_dt,
                              CASE
                                  WHEN ( mt.f1_years > 0
                                         OR mt.f1_months > 0 )
                                       AND mt.f1_days = 0 THEN ( mt.f1_years * 12 ) + mt.f1_months
                                  ELSE 0
                              END AS months_bet_pm,
                              CASE
                                  WHEN mt.f1_days > 0 THEN ( mt.f1_years * 365 ) + ( mt.f1_months * 30 ) + mt.f1_days
                                  ELSE 0
                              END AS days_bet_pm,
                              1 AS asset_percentage
                          FROM
                              assetFcst f,
                              w1_maint_trigger mt,
                              w1_tmpl_wo tw,
                              w1_tmpl_act ta,
                              w1_asset_node an2
                          WHERE
                              mt.maint_trigger_id = f.maint_trigger_id
                              AND tw.tmpl_wo_id = ta.tmpl_wo_id
                              AND tw.tmpl_wo_id = mt.tmpl_wo_id
                              AND tw.tmpl_class_flg = 'W1GN'
                              AND f.asset_id = an2.curr_asset_id
                          UNION ALL
                          SELECT
                              assettw.asset_id,
                              assetmt.maint_trigger_id,
                              assettw.curr_node_id,
                              assettw.tmpl_wo_id,
                              assettw.tmpl_act_id,
                              assetmt.next_maint_dt,
                              assetmt.months_bet_pm,
                              assetmt.days_bet_pm,
                              assettw.asset_percentage / 100 AS asset_percentage
                          FROM
                              (
                                  SELECT
                                      tacast.asset_id,
                                      tacast.curr_node_id,
                                      tacast.asset_type_cd,
                                      tacast.tmpl_wo_id,
                                      tacast.tmpl_act_id,
                                      round(tacast.percentage / COUNT(DISTINCT tacast.asset_id) OVER(
                                          PARTITION BY tacast.tmpl_act_id,tacast.curr_node_id,tacast.costDistAT
                                      ),2) AS asset_percentage
                                  FROM
                                      (
                                          SELECT
                                              a1.asset_id,
                                              a1.asset_type_cd,
                                              an.curr_node_id,
                                              tac.percentage,
                                              tac.tmpl_act_id,
                                              ta.tmpl_wo_id,
                                              tac.asset_type_cd as costDistAT
                                          FROM
                                              w1_tmpl_act_cost_dist tac,
                                              w1_asset_node an,
                                              w1_asset a1,
                                              w1_tmpl_act ta
                                          WHERE
                                              tac.node_id = an.curr_node_id
                                              and a1.asset_id = an.asset_id
                                              AND decode(tac.asset_type_cd,' ',a1.asset_type_cd,tac.asset_type_cd) = a1.asset_type_cd
                                              AND ta.tmpl_act_id = tac.tmpl_act_id
                                             AND an.asset_dpos_flg like 'IN%'
                                          union all
                                          SELECT
                                              a1.asset_id,
                                              a1.asset_type_cd,
                                              an.curr_node_id,
                                              tac.percentage,
                                              tac.tmpl_act_id,
                                              ta.tmpl_wo_id,
                                              tac.asset_type_cd as costDistAT
                                          FROM
                                              w1_tmpl_act_cost_dist tac,
                                              w1_asset_node an,
                                              w1_asset_node cmp,
                                              w1_asset a1,
                                              w1_tmpl_act ta
                                          WHERE
                                              tac.node_id = an.curr_node_id
                                              and cmp.curr_attch_to_asset_id = an.asset_id
                                              and a1.asset_id = cmp.asset_id
                                              AND decode(tac.asset_type_cd,' ',a1.asset_type_cd,tac.asset_type_cd) = a1.asset_type_cd
                                              AND ta.tmpl_act_id = tac.tmpl_act_id
                                             AND an.asset_dpos_flg like 'IN%'
                                             AND cmp.asset_dpos_flg like 'AT%'
                                      ) tacast
                              ) assettw,
                              (
                                  SELECT
                                      mt.maint_trigger_id,
                                      mt.tmpl_wo_id,
                                      f.next_maint_dt,
                                      f.asset_id,
                                     nvl(an2.curr_node_id, (
                                         SELECT
                                             z.curr_node_id
                                         FROM
                                             w1_asset_node z
                                         WHERE
an2.curr_attch_to_asset_id = z.curr_asset_id
                                     ) ) AS node_id,
                                      CASE
                                          WHEN ( mt.f1_years > 0
                                                 OR mt.f1_months > 0 )
                                               AND mt.f1_days = 0 THEN ( mt.f1_years * 12 ) + mt.f1_months
                                          ELSE 0
                                      END AS months_bet_pm,
                                      CASE
                                          WHEN mt.f1_days > 0 THEN ( mt.f1_years * 365 ) + ( mt.f1_months * 30 ) + mt.f1_days
                                          ELSE 0
                                      END AS days_bet_pm
                                  FROM
                                      assetFcst f,
                                      w1_maint_trigger mt,
                                     w1_asset_node an2
                                  WHERE
                                      f.maint_trigger_id = mt.maint_trigger_id
                                      AND an2.curr_asset_id = f.asset_id
                              ) assetmt
                          WHERE
                              assetmt.tmpl_wo_id = assettw.tmpl_wo_id
                      )
              ) trg,
              (
                  SELECT
                      tar.tmpl_act_id,
                      rt.resrc_type_id,
                      sum(tar.w1_quantity * tar.w1_duration) AS tot_labor_hours
                  FROM
                      w1_tmpl_act_rsrc tar,
                      w1_resrc_type rt
                  WHERE
                      rt.resrc_type_id = tar.resrc_type_id
                      AND rt.w1_resrc_class_flg = 'W1CR'
                  group by
                      tar.tmpl_act_id,
                      rt.resrc_type_id
             ) wo_hours,
              w1_asset ast,
              w1_asset_type aty
         WHERE
              trg.asset_id = ast.asset_id
              AND wo_hours.tmpl_act_id = trg.tmpl_act_id
              AND ast.asset_type_cd = aty.asset_type_cd
      )
  GROUP BY
      asset_id,
      resrc_type_id,
      node_id,
      in_service_dt,
      predctd_wear_out_dt,
       acquisition_dt,
       remain_life_yrs,
       owning_access_grp_cd
