-- SELECT logic for CISADM.W1_BI_FORECASTEDASSETPMCOST_VW
WITH assetfcst AS (
    SELECT
        fc.asset_id,
        fc.maint_trigger_id,
        MIN(fc.forecast_dt) AS next_maint_dt
    FROM
        w1_asset_maint_trigger_fcst fc
    WHERE
        fc.forecast_dt >= current_date
    GROUP BY
        fc.asset_id,
        fc.maint_trigger_id
)
SELECT
    asset_id              AS asset_id,
    node_id               AS node_id,
    in_service_dt         AS in_service_dt,
    predctd_wear_out_dt   AS predctd_wear_out_dt,
    acquisition_dt        AS acquisition_dt,
    remain_life_yrs       AS remain_life_yrs,
    SUM(cost_next_yr) AS cost_next_yr,
    SUM(cost_next_2yrs) AS cost_next_2_yrs,
    SUM(cost_next_5yrs) AS cost_next_5_yrs,
    SUM(cost_next_10yrs) AS cost_next_10_yrs,
    SUM(cost_remain_life) AS cost_remain_life,
    SUM(labor_cost_next_yr) AS labor_cost_next_yr,
    SUM(labor_cost_next_2yrs) AS labor_cost_next_2_yrs,
    SUM(labor_cost_next_5yrs) AS labor_cost_next_5_yrs,
    SUM(labor_cost_next_10yrs) AS labor_cost_next_10_yrs,
    SUM(labor_cost_remain_life) AS labor_cost_remain_life,
    SUM(matl_cost_next_yr) AS matl_cost_next_yr,
    SUM(matl_cost_next_2yrs) AS matl_cost_next_2_yrs,
    SUM(matl_cost_next_5yrs) AS matl_cost_next_5_yrs,
    SUM(matl_cost_next_10yrs) AS matl_cost_next_10_yrs,
    SUM(matl_cost_remain_life) AS matl_cost_remain_life,
    SUM(equip_cost_next_yr) AS equip_cost_next_yr,
    SUM(equip_cost_next_2yrs) AS equip_cost_next_2_yrs,
    SUM(equip_cost_next_5yrs) AS equip_cost_next_5_yrs,
    SUM(equip_cost_next_10yrs) AS equip_cost_next_10_yrs,
    SUM(equip_cost_remain_life) AS equip_cost_remain_life,
    SUM(misc_cost_next_yr) AS misc_cost_next_yr,
    SUM(misc_cost_next_2yrs) AS misc_cost_next_2_yrs,
    SUM(misc_cost_next_5yrs) AS misc_cost_next_5_yrs,
    SUM(misc_cost_next_10yrs) AS misc_cost_next_10_yrs,
    SUM(misc_cost_remain_life) AS misc_cost_remain_life,
    owning_access_grp_cd,
    1 AS asset_cnt
FROM
    (
        SELECT
            ast.asset_id,
            trg.node_id,
            trg.tmpl_wo_id,
            trunc(ast.in_service_dt) AS in_service_dt,
            trunc(ast.predctd_wear_out_dt) AS predctd_wear_out_dt,
            trunc(ast.acquisition_dt) AS acquisition_dt,
            trg.months_bet_pm,
            trg.days_bet_pm,
            trg.next_maint_dt,
            wo_cost.tot_cost_amt,
            wo_cost.tot_cost_amt * asset_percentage * num_triggers_next_yr AS cost_next_yr,
            wo_cost.tot_cost_amt * asset_percentage * num_triggers_next_2yrs AS cost_next_2yrs,
            wo_cost.tot_cost_amt * asset_percentage * num_triggers_next_5yrs AS cost_next_5yrs,
            wo_cost.tot_cost_amt * asset_percentage * num_triggers_next_10yrs AS cost_next_10yrs,
            CASE
                WHEN trg.months_bet_pm > 0 THEN
                    wo_cost.tot_cost_amt * asset_percentage * floor((nvl2(trunc(ast.in_service_dt), round(greatest((coalesce(ast.
                    useful_life, aty.useful_life, 0) * 12) - months_between(current_date, trunc(ast.in_service_dt)), 0), 1), 0)) /
                    trg.months_bet_pm)
                ELSE
                    wo_cost.tot_cost_amt * asset_percentage * floor((nvl2(trunc(ast.in_service_dt), round(greatest((coalesce(ast.
                    useful_life, aty.useful_life, 0) * 365) -(current_date - trunc(ast.in_service_dt)), 0), 1), 0)) / trg.days_bet_pm
                    )
            END AS cost_remain_life,
            nvl2(trunc(ast.in_service_dt), round(greatest((coalesce(ast.useful_life, aty.useful_life, 0) * 365) -(current_date - trunc
            (ast.in_service_dt)), 0) / 365, 1), 0) AS remain_life_yrs,
            wo_cost.tot_labor_cost_amt * asset_percentage * num_triggers_next_yr AS labor_cost_next_yr,
            wo_cost.tot_labor_cost_amt * asset_percentage * num_triggers_next_2yrs AS labor_cost_next_2yrs,
            wo_cost.tot_labor_cost_amt * asset_percentage * num_triggers_next_5yrs AS labor_cost_next_5yrs,
            wo_cost.tot_labor_cost_amt * asset_percentage * num_triggers_next_10yrs AS labor_cost_next_10yrs,
            CASE
                WHEN trg.months_bet_pm > 0 THEN
                    wo_cost.tot_labor_cost_amt * asset_percentage * floor((nvl2(trunc(ast.in_service_dt), round(greatest((coalesce(ast.
                    useful_life, aty.useful_life, 0) * 12) - months_between(current_date, trunc(ast.in_service_dt)), 0), 1), 0)) /
                    trg.months_bet_pm)
                ELSE
                    wo_cost.tot_labor_cost_amt * asset_percentage * floor((nvl2(trunc(ast.in_service_dt), round(greatest((coalesce(ast.
                    useful_life, aty.useful_life, 0) * 365) -(current_date - trunc(ast.in_service_dt)), 0), 1), 0)) / trg.days_bet_pm
                    )
            END AS labor_cost_remain_life,
            wo_cost.tot_matl_cost_amt * asset_percentage * num_triggers_next_yr AS matl_cost_next_yr,
            wo_cost.tot_matl_cost_amt * asset_percentage * num_triggers_next_2yrs AS matl_cost_next_2yrs,
            wo_cost.tot_matl_cost_amt * asset_percentage * num_triggers_next_5yrs AS matl_cost_next_5yrs,
            wo_cost.tot_matl_cost_amt * asset_percentage * num_triggers_next_10yrs AS matl_cost_next_10yrs,
            CASE
                WHEN trg.months_bet_pm > 0 THEN
                    wo_cost.tot_matl_cost_amt * asset_percentage * floor((nvl2(trunc(ast.in_service_dt), round(greatest((coalesce(ast.
                    useful_life, aty.useful_life, 0) * 12) - months_between(current_date, trunc(ast.in_service_dt)), 0), 1), 0)) /
                    trg.months_bet_pm)
                ELSE
                    wo_cost.tot_matl_cost_amt * asset_percentage * floor((nvl2(trunc(ast.in_service_dt), round(greatest((coalesce(ast.
                    useful_life, aty.useful_life, 0) * 365) -(current_date - trunc(ast.in_service_dt)), 0), 1), 0)) / trg.days_bet_pm
                    )
            END AS matl_cost_remain_life,
            wo_cost.tot_equip_cost_amt * asset_percentage * num_triggers_next_yr AS equip_cost_next_yr,
            wo_cost.tot_equip_cost_amt * asset_percentage * num_triggers_next_2yrs AS equip_cost_next_2yrs,
            wo_cost.tot_equip_cost_amt * asset_percentage * num_triggers_next_5yrs AS equip_cost_next_5yrs,
            wo_cost.tot_equip_cost_amt * asset_percentage * num_triggers_next_10yrs AS equip_cost_next_10yrs,
            CASE
                WHEN trg.months_bet_pm > 0 THEN
                    wo_cost.tot_equip_cost_amt * asset_percentage * floor((nvl2(trunc(ast.in_service_dt), round(greatest((coalesce(ast.
                    useful_life, aty.useful_life, 0) * 12) - months_between(current_date, trunc(ast.in_service_dt)), 0), 1), 0)) /
                    trg.months_bet_pm)
                ELSE
                    wo_cost.tot_equip_cost_amt * asset_percentage * floor((nvl2(trunc(ast.in_service_dt), round(greatest((coalesce(ast.
                    useful_life, aty.useful_life, 0) * 365) -(current_date - trunc(ast.in_service_dt)), 0), 1), 0)) / trg.days_bet_pm
                    )
            END AS equip_cost_remain_life,
            wo_cost.tot_misc_cost_amt * asset_percentage * num_triggers_next_yr AS misc_cost_next_yr,
            wo_cost.tot_misc_cost_amt * asset_percentage * num_triggers_next_2yrs AS misc_cost_next_2yrs,
            wo_cost.tot_misc_cost_amt * asset_percentage * num_triggers_next_5yrs AS misc_cost_next_5yrs,
            wo_cost.tot_misc_cost_amt * asset_percentage * num_triggers_next_10yrs AS misc_cost_next_10yrs,
            CASE
                WHEN trg.months_bet_pm > 0 THEN
                    wo_cost.tot_misc_cost_amt * asset_percentage * floor((nvl2(trunc(ast.in_service_dt), round(greatest((coalesce(ast.
                    useful_life, aty.useful_life, 0) * 12) - months_between(current_date, trunc(ast.in_service_dt)), 0), 1), 0)) /
                    trg.months_bet_pm)
                ELSE
                    wo_cost.tot_misc_cost_amt * asset_percentage * floor((nvl2(trunc(ast.in_service_dt), round(greatest((coalesce(ast.
                    useful_life, aty.useful_life, 0) * 365) -(current_date - trunc(ast.in_service_dt)), 0), 1), 0)) / trg.days_bet_pm
                    )
            END AS misc_cost_remain_life,
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
                        WHEN months_bet_pm > 0 THEN
                            floor(((months_between(add_months(current_date, 12), next_maint_dt))) / months_bet_pm) + 1
                        ELSE
                            floor(((add_months(current_date, 12) - next_maint_dt)) / days_bet_pm) + 1
                    END AS num_triggers_next_yr,
                    CASE
                        WHEN months_bet_pm > 0 THEN
                            floor(((months_between(add_months(current_date, 24), next_maint_dt))) / months_bet_pm) + 1
                        ELSE
                            floor(((add_months(current_date, 24) - next_maint_dt)) / days_bet_pm) + 1
                    END AS num_triggers_next_2yrs,
                    CASE
                        WHEN months_bet_pm > 0 THEN
                            floor(((months_between(add_months(current_date, 60), next_maint_dt))) / months_bet_pm) + 1
                        ELSE
                            floor(((add_months(current_date, 60) - next_maint_dt)) / days_bet_pm) + 1
                    END AS num_triggers_next_5yrs,
                    CASE
                        WHEN months_bet_pm > 0 THEN
                            floor(((months_between(add_months(current_date, 120), next_maint_dt))) / months_bet_pm) + 1
                        ELSE
                            floor(((add_months(current_date, 120) - next_maint_dt)) / days_bet_pm) + 1
                    END AS num_triggers_next_10yrs,
                    asset_percentage
                FROM
                    (
                        SELECT
                            f.asset_id,
                            f.maint_trigger_id,
                            nvl(an2.curr_node_id,(
                                SELECT
                                    z.curr_node_id
                                FROM
                                    w1_asset_node z
                                WHERE
                                    an2.curr_attch_to_asset_id = z.curr_asset_id
                            )) AS node_id,
                            mt.tmpl_wo_id,
                            ta.tmpl_act_id,
                            next_maint_dt,
                            CASE
                                WHEN ( mt.f1_years > 0
                                       OR mt.f1_months > 0 )
                                     AND mt.f1_days = 0 THEN
                                    ( mt.f1_years * 12 ) + mt.f1_months
                                ELSE
                                    0
                            END AS months_bet_pm,
                            CASE
                                WHEN mt.f1_days > 0 THEN
                                    ( mt.f1_years * 365 ) + ( mt.f1_months * 30 ) + mt.f1_days
                                ELSE
                                    0
                            END AS days_bet_pm,
                            1 AS asset_percentage
                        FROM
                            assetfcst          f,
                            w1_maint_trigger   mt,
                            w1_tmpl_wo         tw,
                            w1_tmpl_act        ta,
                            w1_asset_node      an2
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
                                                                                                                                                --tacast.costDistAT,
                                    round(tacast.percentage / COUNT(DISTINCT tacast.asset_id) OVER(
                                        PARTITION BY tacast.tmpl_act_id, tacast.curr_node_id, tacast.costdistat
                                    ), 2) AS asset_percentage
                                FROM
                                    (
                                        SELECT
                                            a1.asset_id,
                                            a1.asset_type_cd,
                                            an.curr_node_id,
                                            tac.percentage,
                                            tac.tmpl_act_id,
                                            ta.tmpl_wo_id,
                                            tac.asset_type_cd AS costdistat
                                        FROM
                                            w1_tmpl_act_cost_dist   tac,
                                            w1_asset_node           an,
                                            w1_asset                a1,
                                            w1_tmpl_act             ta
                                        WHERE
                                            tac.node_id = an.curr_node_id
                                            AND a1.asset_id = an.asset_id
                                            AND decode(tac.asset_type_cd, ' ', a1.asset_type_cd, tac.asset_type_cd) = a1.asset_type_cd
                                            AND ta.tmpl_act_id = tac.tmpl_act_id
                                            AND an.asset_dpos_flg LIKE 'IN%'
                                        UNION ALL
                                        SELECT
                                            a1.asset_id,
                                            a1.asset_type_cd,
                                            an.curr_node_id,
                                            tac.percentage,
                                            tac.tmpl_act_id,
                                            ta.tmpl_wo_id,
                                            tac.asset_type_cd AS costdistat
                                        FROM
                                            w1_tmpl_act_cost_dist   tac,
                                            w1_asset_node           an,
                                            w1_asset_node           cmp,
                                            w1_asset                a1,
                                            w1_tmpl_act             ta
                                        WHERE
                                            tac.node_id = an.curr_node_id
                                            AND cmp.curr_attch_to_asset_id = an.asset_id
                                            AND a1.asset_id = cmp.asset_id
                                            AND decode(tac.asset_type_cd, ' ', a1.asset_type_cd, tac.asset_type_cd) = a1.asset_type_cd
                                            AND ta.tmpl_act_id = tac.tmpl_act_id
                                            AND an.asset_dpos_flg LIKE 'IN%'
                                            AND cmp.asset_dpos_flg LIKE 'AT%'
                                    ) tacast
                            ) assettw,
                            (
                                SELECT
                                    mt.maint_trigger_id,
                                    mt.tmpl_wo_id,
                                    f.next_maint_dt,
                                    f.asset_id,
                                    nvl(an2.curr_node_id,(
                                        SELECT
                                            z.curr_node_id
                                        FROM
                                            w1_asset_node z
                                        WHERE
                                            an2.curr_attch_to_asset_id = z.curr_asset_id
                                    )) AS node_id,
                                    CASE
                                        WHEN ( mt.f1_years > 0
                                               OR mt.f1_months > 0 )
                                             AND mt.f1_days = 0 THEN
                                            ( mt.f1_years * 12 ) + mt.f1_months
                                        ELSE
                                            0
                                    END AS months_bet_pm,
                                    CASE
                                        WHEN mt.f1_days > 0 THEN
                                            ( mt.f1_years * 365 ) + ( mt.f1_months * 30 ) + mt.f1_days
                                        ELSE
                                            0
                                    END AS days_bet_pm
                                FROM
                                    assetfcst          f,
                                    w1_maint_trigger   mt,
                                    w1_asset_node      an2
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
                    z.tmpl_act_id,
                    SUM(z.tot_cost_amt) as tot_cost_amt,
                    sum(case when z.w1_resrc_class_flg = 'W1CR' then z.tot_cost_amt else 0 end) as tot_labor_cost_amt,
                    sum(case when z.w1_resrc_class_flg = 'W1EQ' then z.tot_cost_amt else 0 end) as tot_equip_cost_amt,
                    sum(case when z.w1_resrc_class_flg = 'W1MT' then z.tot_cost_amt else 0 end) as tot_matl_cost_amt,
                    sum(case when z.w1_resrc_class_flg = 'W1OT' then z.tot_cost_amt else 0 end) as tot_misc_cost_amt
                FROM
                    (
                        SELECT
                            tar.tmpl_act_id,
                            CASE
                                WHEN rt.w1_resrc_class_flg IN (
                                    'W1CR',
                                    'W1EQ'
                                ) THEN
                                    tar.w1_quantity * tar.unit_price * tar.w1_duration
                                ELSE
                                    tar.w1_quantity * tar.unit_price
                            END AS tot_cost_amt,
                            CASE
                                WHEN rt.w1_resrc_class_flg <> ' ' THEN
                                    rt.w1_resrc_class_flg
                                ELSE
                                    'W1MT'
                            END AS w1_resrc_class_flg
                        FROM
                            w1_tmpl_act_rsrc   tar,
                            w1_tmpl_act        ta,
                            w1_resrc_type      rt
                        WHERE
                            tar.tmpl_act_id = ta.tmpl_act_id
                            AND rt.resrc_type_id (+) = tar.resrc_type_id
                    ) z
                GROUP BY
                    z.tmpl_act_id
            ) wo_cost,
            w1_asset        ast,
            w1_asset_type   aty
        WHERE
            trg.asset_id = ast.asset_id
            AND wo_cost.tmpl_act_id = trg.tmpl_act_id
            AND ast.asset_type_cd = aty.asset_type_cd
    )
GROUP BY
    asset_id,
    node_id,
    in_service_dt,
    predctd_wear_out_dt,
    acquisition_dt,
    remain_life_yrs,
    owning_access_grp_cd
