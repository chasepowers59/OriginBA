CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."C1_SA_RS_VW" ("SA_ID", "EFFDT", "RS_CD") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
    "SA_ID","EFFDT","RS_CD"
FROM
    ci_sa_rs_hist a
WHERE
    a.effdt = (
        SELECT
            MAX(b.effdt)
        FROM
            ci_sa_rs_hist b
        WHERE
            a.sa_id = b.sa_id
            AND   b.effdt <= CURRENT_DATE
    );
