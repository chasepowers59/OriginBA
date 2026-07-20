-- CMS Device BO Data Area view expected by Standard Offering Device Domain
-- Device Domain (schemaAlias CISADM).

PROMPT ============================================================
PROMPT Create CISADM.CMS_D1_DVC_BODA_VW (CityCorp / SO)
PROMPT ============================================================

CREATE OR REPLACE FORCE EDITIONABLE VIEW cisadm.cms_d1_dvc_boda_vw (
    d1_device_id,
    bus_obj_cd,
    status,
    retirement_dttm
) AS
SELECT
    dvc.d1_device_id,
    MIN(dvc.bus_obj_cd) AS bus_obj_cd,
    CAST(MIN(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', dvc.bo_data_area), '</root>')), 'root/latestBoStatus')) AS CHAR(12)) AS status,
    MIN(TO_DATE(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', dvc.bo_data_area), '</root>')), 'root/retirementDateTime'), 'YYYY-MM-DD-HH24.MI.SS')) AS retirement_dttm
FROM cisadm.d1_dvc dvc
WHERE dvc.bo_data_area IS NOT NULL
GROUP BY dvc.d1_device_id;

GRANT SELECT ON cisadm.cms_d1_dvc_boda_vw TO cis_read;
GRANT SELECT ON cisadm.cms_d1_dvc_boda_vw TO cis_user;
GRANT SELECT ON cisadm.cms_d1_dvc_boda_vw TO cisread;
GRANT SELECT ON cisadm.cms_d1_dvc_boda_vw TO cisuser;
GRANT SELECT ON cisadm.cms_d1_dvc_boda_vw TO jrs2c2m;

CREATE OR REPLACE SYNONYM cisread.cms_d1_dvc_boda_vw FOR cisadm.cms_d1_dvc_boda_vw;

PROMPT CMS_D1_DVC_BODA_VW created.
