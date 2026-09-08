-- Governance filter reference for periodic reports.
-- See sql/governance_snippets.sql for full commentary.

-- Active service agreements only:
--   NULLIF(TRIM(sa_status_flg), '') = '20'

-- Frozen financial transactions (when querying CI_FT directly):
--   freeze_sw = 'Y'

-- Completed / frozen bill segments (when querying CI_BSEG directly):
--   NULLIF(TRIM(bseg_stat_flg), '') = '50'

-- Exclude synthetic Odessa test rows:
--   acct_id NOT LIKE 'ODEV%'
--   bseg_id NOT LIKE 'ODEV%'

-- Arrears analysis (exclude payments):
--   ft_type_flg NOT IN ('PS', 'PX')
--   NOT_IN_ARS_SW = 'N'
--   ars_dt IS NOT NULL
