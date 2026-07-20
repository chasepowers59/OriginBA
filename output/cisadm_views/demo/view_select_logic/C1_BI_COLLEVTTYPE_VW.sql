-- SELECT logic for CISADM.C1_BI_COLLEVTTYPE_VW
SELECT
      cast(concat('C',cl.coll_evt_typ_cd) as char(12)) collectible_evt_type_cd,
      cl.descr
  FROM
      ci_coll_evt_typ_l cl
  WHERE
      language_cd = 'ENG'
  UNION
  SELECT
      cast(concat('S',sl.sev_evt_type_cd) as char(12)) collectible_evt_type_cd,
      sl.descr
  FROM
      ci_sev_evt_type_l sl
  WHERE
      language_cd = 'ENG'
