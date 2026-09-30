-- Service Agreement 360 (Service_Agreement___Domain / JoinTree_1):
-- live CISADM premise-character join fan-out check (read-only).
--
--   python3 scripts/local/run_client_oracle_sql.py --client <client> \
--     --file sql/validation/service_agreement_prem_char_grain_check.sql

-- 1) Baseline: one row per SA on CI_SA
SELECT 'CI_SA grain' AS gate,
       COUNT(*) AS row_cnt,
       COUNT(DISTINCT sa_id) AS distinct_sa_cnt
FROM cisadm.ci_sa;

-- 2) Fan-out when prem char is joined on CHAR_PREM_ID (expected > distinct SA if chars exist)
SELECT 'SA + CI_PREM_CHAR join' AS gate,
       COUNT(*) AS row_cnt,
       COUNT(DISTINCT sa.sa_id) AS distinct_sa_cnt
FROM cisadm.ci_sa sa
LEFT JOIN cisadm.ci_prem_char pc
  ON pc.prem_id = sa.char_prem_id;

-- 3) Sample SAs where prem char join multiplies rows (for Ad Hoc awareness)
WITH joined AS (
  SELECT sa.sa_id, COUNT(*) AS row_cnt
  FROM cisadm.ci_sa sa
  LEFT JOIN cisadm.ci_prem_char pc
    ON pc.prem_id = sa.char_prem_id
  GROUP BY sa.sa_id
)
SELECT 'SA fan-out from prem char' AS gate, sa_id, row_cnt
FROM joined
WHERE row_cnt > 1
ORDER BY row_cnt DESC
FETCH FIRST 25 ROWS ONLY;

-- 4) Premise with no SA char prem link still appears once (left join preserves SA)
SELECT 'SA with null CHAR_PREM_ID' AS gate,
       COUNT(*) AS sa_cnt
FROM cisadm.ci_sa
WHERE char_prem_id IS NULL;

-- 5) Derived-table contract (the domain's CI_PREM_CHAR is now a jdbcQuery):
--    same row count as the raw table (nothing removed), exactly one current version
--    per (premise, type) that has a non-future version, and a resolved value on every row.
SELECT 'derived CI_PREM_CHAR' AS gate,
       (SELECT COUNT(*) FROM cisadm.ci_prem_char) AS raw_rows,
       COUNT(*) AS derived_rows,
       SUM(CASE WHEN is_current_sw = 'Y' THEN 1 ELSE 0 END) AS current_rows,
       COUNT(DISTINCT CASE WHEN effdt <= CURRENT_DATE THEN prem_id || '|' || char_type_cd END) AS keys_with_a_current_version,
       SUM(CASE WHEN char_value IS NULL THEN 1 ELSE 0 END) AS unresolved_values
FROM (
  SELECT c.prem_id, c.char_type_cd, c.effdt,
         CASE TRIM(ct.char_type_flg) WHEN 'ADV' THEN c.adhoc_char_val WHEN 'FKV' THEN c.char_val_fk1
              ELSE COALESCE(cvl.descr, c.char_val) END AS char_value,
         CASE WHEN c.effdt = MAX(CASE WHEN c.effdt <= CURRENT_DATE THEN c.effdt END)
                   OVER (PARTITION BY c.prem_id, c.char_type_cd) THEN 'Y' ELSE 'N' END AS is_current_sw
  FROM cisadm.ci_prem_char c
  LEFT JOIN cisadm.ci_char_type ct ON ct.char_type_cd = c.char_type_cd
  LEFT JOIN cisadm.ci_char_val_l cvl ON cvl.char_type_cd = c.char_type_cd AND cvl.char_val = c.char_val AND cvl.language_cd = 'ENG'
) d;
-- expect: derived_rows = raw_rows; current_rows = keys_with_a_current_version; unresolved_values = 0

-- 6) The Ad Hoc "Characteristic Type Code" list: types actually used on premises vs every type in the system
SELECT 'prem char types in use vs all types' AS gate,
       (SELECT COUNT(DISTINCT char_type_cd) FROM cisadm.ci_prem_char) AS types_on_premises,
       (SELECT COUNT(*) FROM cisadm.ci_char_type) AS types_in_system
FROM dual;
