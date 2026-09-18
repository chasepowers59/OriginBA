-- Fond du Lac asset domain: why "Current Location/Organization ID" is empty for some meters,
-- and the proof the fixed SC_CURRENT_DISPOSITION query answers every asset. READ ONLY.
--
-- W1_ASSET_NODE is the asset's placement history, one row per (ASSET_ID, EFF_DTTM). The
-- application marks ONE row per asset as current by filling CURR_ASSET_ID / CURR_NODE_ID
-- (measured 2026-09-18 on Ellensburg: 580 assets, exactly one CURR row each, null on every
-- history row; NODE_ID is filled on every row). The legacy domain picked the row with the
-- latest EFF_DTTM instead, and the report reads CURR_NODE_ID from it -- empty whenever the
-- latest-dated row is not the row the application calls current.

-- 1. The meter from the ticket: every placement row, with the application's current marker.
SELECT an.asset_id, an.eff_dttm, an.asset_dpos_flg, an.node_id, an.curr_node_id, an.curr_asset_id, an.act_id
FROM   cisadm.w1_asset_node an
WHERE  an.asset_id IN (SELECT ai.asset_id FROM cisadm.w1_asset_identifier ai
                       WHERE ai.asset_id_type_flg = 'W1BN' AND TRIM(ai.w1_id_value) = '52222349')
ORDER  BY an.eff_dttm;

-- 2. How many assets the legacy rule answers wrongly (latest-dated row is not the current row).
SELECT COUNT(*) AS assets_latest_row_not_current
FROM   cisadm.w1_asset_node an
WHERE  an.eff_dttm = (SELECT MAX(a2.eff_dttm) FROM cisadm.w1_asset_node a2
                      WHERE a2.asset_id = an.asset_id AND a2.eff_dttm <= SYSDATE)
AND    an.curr_asset_id IS NULL;

-- 3. The fixed rule: one row per asset, and a location on every one of them.
SELECT COUNT(*) AS assets, COUNT(curr_node_id) AS with_current_location, MAX(n) AS max_rows_per_asset
FROM  (SELECT an.asset_id, an.curr_node_id, COUNT(*) OVER (PARTITION BY an.asset_id) AS n
       FROM   cisadm.w1_asset_node an
       WHERE  an.eff_dttm = (SELECT COALESCE(MAX(CASE WHEN a2.curr_asset_id IS NOT NULL THEN a2.eff_dttm END),
                                             MAX(CASE WHEN a2.eff_dttm <= SYSDATE THEN a2.eff_dttm END))
                             FROM cisadm.w1_asset_node a2 WHERE a2.asset_id = an.asset_id));
