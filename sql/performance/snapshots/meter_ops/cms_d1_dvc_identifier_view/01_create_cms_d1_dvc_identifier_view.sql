-- CMS Device Identifier view expected by Standard Offering Device Domain
-- Device Domain (schemaAlias CISADM).
--
-- CityCorp had an INVALID CISADM290 copy while CISREAD synonym pointed to
-- missing CISADM object; this creates the expected view, grants, and synonym.

PROMPT ============================================================
PROMPT Create CISADM.CMS_D1_DVC_IDENTIFIER_VW (CityCorp / SO)
PROMPT ============================================================

CREATE OR REPLACE FORCE EDITIONABLE VIEW cisadm.cms_d1_dvc_identifier_vw (
    d1_device_id,
    asset_id,
    badge_number,
    configuration,
    external_id,
    internal_meter_number,
    mdm_external_id,
    nic_id,
    pallet_number,
    serial_number,
    specification,
    neuron_id,
    name,
    nic_serial_number,
    utility_device_id
) AS
SELECT
    d1_device_id,
    CAST(MIN(asset_id) AS VARCHAR2(60)) AS asset_id,
    CAST(MIN(badge_number) AS VARCHAR2(60)) AS badge_number,
    CAST(MIN(configuration) AS VARCHAR2(60)) AS configuration,
    CAST(MIN(external_id) AS VARCHAR2(60)) AS external_id,
    CAST(MIN(internal_meter_number) AS VARCHAR2(60)) AS internal_meter_number,
    CAST(MIN(mdm_external_id) AS VARCHAR2(14)) AS mdm_external_id,
    CAST(MIN(nic_id) AS VARCHAR2(120)) AS nic_id,
    CAST(MIN(pallet_number) AS VARCHAR2(14)) AS pallet_number,
    CAST(MIN(serial_number) AS VARCHAR2(60)) AS serial_number,
    CAST(MIN(specification) AS VARCHAR2(60)) AS specification,
    CAST(MIN(neuron_id) AS VARCHAR2(60)) AS neuron_id,
    CAST(MIN(name) AS VARCHAR2(60)) AS name,
    CAST(MIN(nic_serial_number) AS VARCHAR2(60)) AS nic_serial_number,
    CAST(MIN(utility_device_id) AS VARCHAR2(60)) AS utility_device_id
FROM (
    SELECT
        d1_device_id,
        DECODE(TRIM(dvc_id_type_flg), 'D1AS', TRIM(id_value), NULL) AS asset_id,
        DECODE(TRIM(dvc_id_type_flg), 'D1BN', TRIM(id_value), NULL) AS badge_number,
        DECODE(TRIM(dvc_id_type_flg), 'D1CO', TRIM(id_value), NULL) AS configuration,
        DECODE(TRIM(dvc_id_type_flg), 'D1EI', TRIM(id_value), NULL) AS external_id,
        DECODE(TRIM(dvc_id_type_flg), 'D1IN', TRIM(id_value), NULL) AS internal_meter_number,
        DECODE(TRIM(dvc_id_type_flg), 'D1MI', TRIM(id_value), NULL) AS mdm_external_id,
        DECODE(TRIM(dvc_id_type_flg), 'D1NI', TRIM(id_value), NULL) AS nic_id,
        DECODE(TRIM(dvc_id_type_flg), 'D1PN', TRIM(id_value), NULL) AS pallet_number,
        DECODE(TRIM(dvc_id_type_flg), 'D1SN', TRIM(id_value), NULL) AS serial_number,
        DECODE(TRIM(dvc_id_type_flg), 'D1SP', TRIM(id_value), NULL) AS specification,
        DECODE(TRIM(dvc_id_type_flg), 'D4NR', TRIM(id_value), NULL) AS neuron_id,
        DECODE(TRIM(dvc_id_type_flg), 'D7NA', TRIM(id_value), NULL) AS name,
        DECODE(TRIM(dvc_id_type_flg), 'D7NS', TRIM(id_value), NULL) AS nic_serial_number,
        DECODE(TRIM(dvc_id_type_flg), 'D7UD', TRIM(id_value), NULL) AS utility_device_id
    FROM cisadm.d1_dvc_identifier
)
GROUP BY d1_device_id;

GRANT SELECT ON cisadm.cms_d1_dvc_identifier_vw TO cis_read;
GRANT SELECT ON cisadm.cms_d1_dvc_identifier_vw TO cis_user;
GRANT SELECT ON cisadm.cms_d1_dvc_identifier_vw TO cisread;
GRANT SELECT ON cisadm.cms_d1_dvc_identifier_vw TO cisuser;
GRANT SELECT ON cisadm.cms_d1_dvc_identifier_vw TO jrs2c2m;

CREATE OR REPLACE SYNONYM cisread.cms_d1_dvc_identifier_vw FOR cisadm.cms_d1_dvc_identifier_vw;

PROMPT CMS_D1_DVC_IDENTIFIER_VW created.
