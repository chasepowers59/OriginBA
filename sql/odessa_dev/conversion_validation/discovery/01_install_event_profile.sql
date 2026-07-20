-- Discovery: install event status + on/off history profile (informational).
-- Empty result is fine; this gate never fails CI.

PROMPT === Install event status distribution (ManualMeterInstallEvent) ===

SELECT bo_status_cd,
       COUNT(*) AS install_cnt
FROM cisadm.d1_install_evt
WHERE bus_obj_cd = 'D1-ManualMeterInstallEvent'
GROUP BY bo_status_cd
ORDER BY install_cnt DESC;

PROMPT === Latest on/off history vs install status (active installs, no removal date) ===

WITH latest AS (
  SELECT install_evt_id,
         onoff_hist_flg,
         ROW_NUMBER() OVER (
           PARTITION BY install_evt_id
           ORDER BY evt_dttm DESC, seqno DESC
         ) AS rn
  FROM cisadm.d1_on_off_hist
)
SELECT ie.bo_status_cd,
       l.onoff_hist_flg AS latest_onoff,
       COUNT(*) AS cnt
FROM cisadm.d1_install_evt ie
LEFT JOIN latest l
       ON l.install_evt_id = ie.install_evt_id
      AND l.rn = 1
WHERE ie.bus_obj_cd = 'D1-ManualMeterInstallEvent'
  AND ie.d1_removal_dttm IS NULL
GROUP BY ie.bo_status_cd, l.onoff_hist_flg
ORDER BY cnt DESC;

PROMPT === Off alignment summary (C2M expectation: D1OF + no removal => OFF) ===

WITH latest AS (
  SELECT install_evt_id,
         onoff_hist_flg,
         ROW_NUMBER() OVER (
           PARTITION BY install_evt_id
           ORDER BY evt_dttm DESC, seqno DESC
         ) AS rn
  FROM cisadm.d1_on_off_hist
)
SELECT ie.bo_status_cd,
       COUNT(*) AS should_look_off_cnt
FROM cisadm.d1_install_evt ie
JOIN latest l
  ON l.install_evt_id = ie.install_evt_id
 AND l.rn = 1
WHERE ie.bus_obj_cd = 'D1-ManualMeterInstallEvent'
  AND l.onoff_hist_flg = 'D1OF'
  AND ie.d1_removal_dttm IS NULL
GROUP BY ie.bo_status_cd
ORDER BY should_look_off_cnt DESC;
