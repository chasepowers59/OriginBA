-- Fond du Lac asset domain: why "Current Location/Organization ID" is empty for some meters.
-- READ ONLY. Measured on the Fond du Lac 25.4 TEST instance, 2026-09-18.
--
-- W1_ASSET_NODE is the asset's placement history, one row per (ASSET_ID, EFF_DTTM). The domain
-- picks the latest-dated row (which is what C2M's Disposition History shows as current), and the
-- report reads CURR_NODE_ID from it. CURR_NODE_ID / CURR_ASSET_ID are a denormalised "current"
-- pointer the application maintains on ONE row per asset -- and on two Fond du Lac meters that
-- pointer stayed on an earlier In Store row when the meter was re-installed five minutes later
-- (meter 52222349: 09:00 NI-INSTORE carries the pointer, 09:05 IN-INSTALLED does not). NODE_ID is
-- filled on every row (43,600 of 43,600 latest rows), so the location is always there; the
-- report was reading the wrong column. Selecting by the pointer instead (the first attempt)
-- shows those meters as In Store: worse. The fix keeps the latest row and falls back to NODE_ID.

-- 1. The meter from the ticket: every placement row, with the application's pointer.
SELECT an.asset_id, an.eff_dttm, an.asset_dpos_flg, an.node_id, an.curr_node_id, an.curr_asset_id
FROM   cisadm.w1_asset_node an
WHERE  an.asset_id IN (SELECT ai.asset_id FROM cisadm.w1_asset_identifier ai
                       WHERE ai.asset_id_type_flg = 'W1BN' AND TRIM(ai.w1_id_value) = '52222349')
ORDER  BY an.eff_dttm;

-- 2. Every asset the legacy domain shows without a location (TEST: 2 -- serials 52222349 and 20160346).
SELECT ai.w1_id_value AS serial, an.asset_id, an.eff_dttm, an.asset_dpos_flg, an.node_id
FROM   cisadm.w1_asset_node an
JOIN   cisadm.w1_asset_identifier ai ON ai.asset_id = an.asset_id AND ai.asset_id_type_flg = 'W1BN'
WHERE  an.eff_dttm = (SELECT MAX(a2.eff_dttm) FROM cisadm.w1_asset_node a2 WHERE a2.asset_id = an.asset_id AND a2.eff_dttm <= SYSDATE)
AND    an.curr_node_id IS NULL;

-- 3. The fixed derived table: one row per asset, a location on every one (TEST: 43,600 / 43,600).
SELECT COUNT(*) AS assets, COUNT(curr_node_id) AS with_current_location, MAX(n) AS max_rows_per_asset
FROM  (SELECT an.asset_id, NVL(an.curr_node_id, an.node_id) AS curr_node_id, COUNT(*) OVER (PARTITION BY an.asset_id) AS n
       FROM   cisadm.w1_asset_node an
       WHERE  an.eff_dttm = (SELECT MAX(a2.eff_dttm) FROM cisadm.w1_asset_node a2 WHERE a2.asset_id = an.asset_id AND a2.eff_dttm <= SYSDATE));
