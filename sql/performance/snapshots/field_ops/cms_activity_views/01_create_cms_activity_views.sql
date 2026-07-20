-- CMS Field Activity enrichment views expected by Standard Offering
-- Field Activity Domain (schemaAlias CISADM).
--
-- CityCorp had these only under CISADM290 (INVALID), while CISREAD synonyms
-- pointed at missing CISADM objects — same gap pattern as CMS_SA_SNAPSHOT.
--
-- Views:
--   CISADM.CMS_C1_REPRESENTATIVE_BODA_VW
--   CISADM.CMS_D1_ACTIVITY_CHAR_VW
--   CISADM.CMS_D1_ACTIVITY_D1FA_BODA_VW

PROMPT ============================================================
PROMPT Create CISADM CMS Field Activity views (CityCorp / SO)
PROMPT ============================================================

CREATE OR REPLACE FORCE EDITIONABLE VIEW cisadm.cms_c1_representative_boda_vw (
    c1_representative_cd,
    cm_ml_svc_area,
    cm_ml_worker_capability
) AS
SELECT
    rep.c1_representative_cd,
    CAST(svc_area.cm_ml_svc_area AS VARCHAR2(30)) AS cm_ml_svc_area,
    CAST(work_capability.cm_ml_worker_capability AS VARCHAR2(16)) AS cm_ml_worker_capability
FROM cisadm.c1_representative rep
LEFT JOIN XMLTABLE(
    '/root/cmMobileLiteDetails/serviceAreas/serviceAreaList'
    PASSING XMLTYPE(CONCAT(CONCAT('<root>', rep.bo_data_area), '</root>'))
    COLUMNS cm_ml_svc_area VARCHAR2(50) PATH 'serviceArea'
) svc_area ON 1 = 1
LEFT JOIN XMLTABLE(
    '/root/cmMobileLiteDetails/workerCapability/capabilities'
    PASSING XMLTYPE(CONCAT(CONCAT('<root>', rep.bo_data_area), '</root>'))
    COLUMNS cm_ml_worker_capability VARCHAR2(50) PATH 'capability'
) work_capability ON 1 = 1;

CREATE OR REPLACE FORCE EDITIONABLE VIEW cisadm.cms_d1_activity_char_vw (
    d1_activity_id,
    fa_int_status_flg,
    fa_priority_flg,
    thrd_pty_rep_cd
) AS
SELECT
    d1_activity_id,
    MIN(fa_int_status_flg) AS fa_int_status_flg,
    MIN(fa_priority_flg) AS fa_priority_flg,
    MIN(thrd_pty_rep_cd) AS thrd_pty_rep_cd
FROM (
    SELECT
        ac.d1_activity_id,
        DECODE(TRIM(ac.char_type_cd), 'CMFAINST', ac.srch_char_val, ' ') AS fa_int_status_flg,
        DECODE(TRIM(ac.char_type_cd), 'CMFAPRIO', ac.srch_char_val, ' ') AS fa_priority_flg,
        DECODE(TRIM(ac.char_type_cd), 'CMFAREP', ac.srch_char_val, ' ') || '  ' AS thrd_pty_rep_cd
    FROM cisadm.d1_activity_char ac
)
GROUP BY d1_activity_id;

CREATE OR REPLACE FORCE EDITIONABLE VIEW cisadm.cms_d1_activity_d1fa_boda_vw (
    d1_activity_id,
    comments,
    d1_instructions,
    appointment_flg,
    appointment_window_start_dttm,
    appointment_window_end_dttm,
    appointment_taken_by,
    appointment_taken_date,
    appointment_comments,
    expiration_dttm,
    cr_requester_user,
    ext_reference_id,
    d1_cont_external_id,
    d1_customername,
    d1_contactname,
    d1_mainphone,
    d1_cellphone,
    email_value,
    external_acct_id,
    cm_ml_is_pickup_flg
) AS
SELECT
    act.d1_activity_id,
    CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', act.bo_data_area), '</root>')), 'root/comments') AS VARCHAR2(254)) AS comments,
    CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', act.bo_data_area), '</root>')), 'root/instructions') AS VARCHAR2(4000)) AS d1_instructions,
    CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', act.bo_data_area), '</root>')), 'root/isAppointmentNecessary') AS VARCHAR2(1)) AS appointment_flg,
    CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', act.bo_data_area), '</root>')), 'root/appointmentWindow/startDateTime') AS VARCHAR2(26)) AS appointment_window_start_dttm,
    CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', act.bo_data_area), '</root>')), 'root/appointmentWindow/endDateTime') AS VARCHAR2(26)) AS appointment_window_end_dttm,
    CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', act.bo_data_area), '</root>')), 'root/appointmentInformation/takenBy') AS VARCHAR2(32)) AS appointment_taken_by,
    CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', act.bo_data_area), '</root>')), 'root/appointmentInformation/takenDate') AS VARCHAR2(32)) AS appointment_taken_date,
    CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', act.bo_data_area), '</root>')), 'root/appointmentInformation/comments') AS VARCHAR2(254)) AS appointment_comments,
    CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', act.bo_data_area), '</root>')), 'root/expirationDateTime') AS VARCHAR2(26)) AS expiration_dttm,
    CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', act.bo_data_area), '</root>')), 'root/requesterUserId') AS VARCHAR2(8)) AS cr_requester_user,
    CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', act.bo_data_area), '</root>')), 'root/externalReferenceId') AS VARCHAR2(36)) AS ext_reference_id,
    CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', act.bo_data_area), '</root>')), 'root/contactDetails/personId') AS VARCHAR2(60)) AS d1_cont_external_id,
    CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', act.bo_data_area), '</root>')), 'root/contactDetails/customerName') AS VARCHAR2(50)) AS d1_customername,
    CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', act.bo_data_area), '</root>')), 'root/contactDetails/contactName') AS VARCHAR2(50)) AS d1_contactname,
    CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', act.bo_data_area), '</root>')), 'root/contactDetails/mainPhone') AS VARCHAR2(24)) AS d1_mainphone,
    CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', act.bo_data_area), '</root>')), 'root/contactDetails/cellPhone') AS VARCHAR2(24)) AS d1_cellphone,
    CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', act.bo_data_area), '</root>')), 'root/contactDetails/email') AS VARCHAR2(254)) AS email_value,
    CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', act.bo_data_area), '</root>')), 'root/contactDetails/accountId') AS VARCHAR2(30)) AS external_acct_id,
    CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', act.bo_data_area), '</root>')), 'root/cmMobileLiteDetails/isPickupOrder') AS VARCHAR2(1)) AS cm_ml_is_pickup_flg
FROM cisadm.d1_activity act
INNER JOIN cisadm.d1_activity_type actty
    ON actty.activity_type_cd = act.activity_type_cd
   AND actty.activity_type_cat_flg = 'D1FA';

GRANT SELECT ON cisadm.cms_c1_representative_boda_vw TO cis_read;
GRANT SELECT ON cisadm.cms_c1_representative_boda_vw TO cis_user;
GRANT SELECT ON cisadm.cms_c1_representative_boda_vw TO cisread;
GRANT SELECT ON cisadm.cms_c1_representative_boda_vw TO cisuser;
GRANT SELECT ON cisadm.cms_c1_representative_boda_vw TO jrs2c2m;

GRANT SELECT ON cisadm.cms_d1_activity_char_vw TO cis_read;
GRANT SELECT ON cisadm.cms_d1_activity_char_vw TO cis_user;
GRANT SELECT ON cisadm.cms_d1_activity_char_vw TO cisread;
GRANT SELECT ON cisadm.cms_d1_activity_char_vw TO cisuser;
GRANT SELECT ON cisadm.cms_d1_activity_char_vw TO jrs2c2m;

GRANT SELECT ON cisadm.cms_d1_activity_d1fa_boda_vw TO cis_read;
GRANT SELECT ON cisadm.cms_d1_activity_d1fa_boda_vw TO cis_user;
GRANT SELECT ON cisadm.cms_d1_activity_d1fa_boda_vw TO cisread;
GRANT SELECT ON cisadm.cms_d1_activity_d1fa_boda_vw TO cisuser;
GRANT SELECT ON cisadm.cms_d1_activity_d1fa_boda_vw TO jrs2c2m;

-- Fix invalid CISREAD synonyms that pointed at missing CISADM objects.
CREATE OR REPLACE SYNONYM cisread.cms_c1_representative_boda_vw FOR cisadm.cms_c1_representative_boda_vw;
CREATE OR REPLACE SYNONYM cisread.cms_d1_activity_char_vw FOR cisadm.cms_d1_activity_char_vw;
CREATE OR REPLACE SYNONYM cisread.cms_d1_activity_d1fa_boda_vw FOR cisadm.cms_d1_activity_d1fa_boda_vw;

PROMPT CMS Field Activity views created.
