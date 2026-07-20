-- SELECT logic for CISADM.W1_BI_ASSETCOST_VW
SELECT
    a.asset_id AS asset_id,
    nvl(an.curr_node_id,(
        SELECT
            an2.curr_node_id
        FROM
            w1_asset_node an2
        WHERE
            an2.curr_asset_id = an.curr_attch_to_asset_id
    )) AS node_id,
    nvl(total_maint_cost, 0) AS total_maintenance_cost,
    nvl(total_renewal_cost, 0) AS total_renewal_cost,
    nvl(total_cm_maint_cost, 0) AS total_cm_maint_cost,
    nvl(total_pm_maint_cost, 0) AS total_pm_maint_cost,
    nvl((total_maint_cost + total_renewal_cost), 0) AS w1_bi_total_cost,
    nvl(total_failure_repair_cost, 0) AS total_fail_repr_cost,
    nvl(total_failure_cnt, 0) AS total_failure_count,
    nvl(
        CASE
            WHEN total_failure_cnt > 0 THEN
                round((total_failure_repair_cost / total_failure_cnt), 2)
            ELSE
                0
        END, 0) AS avg_fail_repr_cost,
    nvl(nvl(a.acquisition_cost, 0) + total_cost, 0) AS asset_life_to_dt_cost,
    nvl(cost_past_12months, 0) AS past_12months_cost,
    nvl(cost_past13_24months, 0) AS past_13_24months_cost,
    nvl(cost_past25_36months, 0) AS past_25_36months_cost,
    nvl(cost_past_3years, 0) AS past_3years_cost,
    nvl(avg_cost_past_3years, 0) AS avg_past_3years_cost,
    decode(nvl(a.replacement_cost, 0), 0, 0, round(((cost_purchase / a.replacement_cost) * 100), 2)) AS percent_purchase,
    trunc(a.acquisition_dt) AS acquisition_dt,
    nvl(a.avg_out_repr_cost, 0) AS avg_out_repr_cost,
    trunc(a.core_chrg_exp_dt) AS core_chrg_exp_dt,
    trunc(a.in_service_dt) AS in_service_dt,
    trunc(a.predctd_wear_out_dt) AS predctd_wear_out_dt,
    a.owning_access_grp_cd as owning_access_grp_cd,
    1 AS asset_count
FROM
    w1_asset        a
    JOIN w1_asset_node   an ON an.curr_asset_id = a.asset_id
    LEFT OUTER JOIN (
        SELECT
            asset_id,
            SUM(maintenance_cost) AS total_maint_cost,
            SUM(renewal_cost) AS total_renewal_cost,
            SUM(w1_bi_total_cost) AS total_cost,
            SUM(failure_repair_cost) AS total_failure_repair_cost,
            SUM(failure_count) AS total_failure_cnt,
            SUM(
                CASE
                    WHEN renewal_flg = 'W1NO' THEN
                        maintenance_cm_cost
                    ELSE
                        0
                END
            ) AS total_cm_maint_cost,
            SUM(
                CASE
                    WHEN renewal_flg = 'W1NO' THEN
                        maintenance_pm_cost
                    ELSE
                        0
                END
            ) AS total_pm_maint_cost,
            SUM(
                CASE
                    WHEN add_months(current_date, - 12) <= cost.act_cre_dttm THEN
                        w1_bi_total_cost
                    ELSE
                        0
                END
            ) AS cost_past_12months,
            SUM(
                CASE
                    WHEN cost.act_cre_dttm >= add_months(current_date, - 24)
                         AND cost.act_cre_dttm < add_months(current_date, - 12) THEN
                        w1_bi_total_cost
                    ELSE
                        0
                END
            ) AS cost_past13_24months,
            SUM(
                CASE
                    WHEN cost.act_cre_dttm >= add_months(current_date, - 36)
                         AND cost.act_cre_dttm < add_months(current_date, - 24) THEN
                        w1_bi_total_cost
                    ELSE
                        0
                END
            ) AS cost_past25_36months,
            SUM(
                CASE
                    WHEN add_months(current_date, - 36) <= cost.act_cre_dttm THEN
                        w1_bi_total_cost
                    ELSE
                        0
                END
            ) AS cost_past_3years,
            round(SUM(
                CASE
                    WHEN add_months(current_date, - 36) <= cost.act_cre_dttm THEN
                        w1_bi_total_cost
                    ELSE
                        0
                END
            ) / 3, 2) AS avg_cost_past_3years,
            ( SUM(
                CASE
                    WHEN add_months(current_date, - 36) <= cost.act_cre_dttm THEN
                        w1_bi_total_cost
                    ELSE
                        0
                END
            ) / 3 ) cost_purchase
        FROM
            w1_bi_assetactcost_vw cost
        GROUP BY
            cost.asset_id
    ) vw ON vw.asset_id = a.asset_id
