-- WARN gate: frozen bill segments without matching CI_FT on same bill+SA.

PROMPT === Gate billing: frozen bseg without FT (WARN sample) ===

SELECT 'bseg_without_ft' AS check_id,
       'WARN' AS severity,
       bs.bseg_id,
       bs.bill_id,
       bs.sa_id,
       bs.bseg_stat_flg
FROM cisadm.ci_bseg bs
JOIN cisadm.ci_bill b ON b.bill_id = bs.bill_id
WHERE b.bill_stat_flg = 'C '
  AND bs.bseg_stat_flg = '50'
  AND bs.bseg_id NOT LIKE 'ODEV%'
  AND NOT EXISTS (
        SELECT 1 FROM cisadm.ci_ft ft
         WHERE ft.bill_id = bs.bill_id
           AND ft.sa_id = bs.sa_id
      )
ORDER BY bs.bill_id DESC
FETCH FIRST 50 ROWS ONLY;
