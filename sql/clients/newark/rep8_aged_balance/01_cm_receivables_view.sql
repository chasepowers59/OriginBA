-- Newark REP8 legacy support object: receivable FT grain for bucket math in REP8_VW.
-- Replaces missing JRS2C2M.CM_RECEIVABLES staging table from pre-25.4 Newark reporting.

PROMPT Creating JRS2C2M.CM_RECEIVABLES view...

CREATE OR REPLACE VIEW jrs2c2m.cm_receivables AS
SELECT
    sa.acct_id,
    ft.cur_amt,
    ft.ars_dt,
    NVL(ft.parent_id, ' ') AS parent_id
FROM cisadm.ci_ft ft
JOIN cisadm.ci_sa sa
  ON sa.sa_id = ft.sa_id
WHERE ft.freeze_sw = 'Y'
  AND ft.not_in_ars_sw = 'N'
  AND ft.ars_dt IS NOT NULL
  AND ft.ft_type_flg NOT IN ('PS', 'PX');
