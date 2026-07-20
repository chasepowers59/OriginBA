-- CMS Asset Identifier view expected by Standard Offering Asset Domain
-- Asset Domain (schemaAlias CISADM).
--
-- CityCorp had CISREAD synonym pointing to missing CISADM object;
-- this creates the expected view, grants, and synonym.

PROMPT ============================================================
PROMPT Create CISADM.CMS_W1_ASSET_IDENTIFIER_VW (CityCorp / SO)
PROMPT ============================================================

CREATE OR REPLACE FORCE EDITIONABLE VIEW cisadm.cms_w1_asset_identifier_vw (
    asset_id,
    external_id,
    pallet_number,
    serial_number,
    badge_number,
    purchase_order,
    metrology_firmware_version,
    nic_firmware_version
) AS
SELECT
    asset_id,
    CAST(MIN(external_id) AS VARCHAR2(60)) AS external_id,
    CAST(MIN(pallet_number) AS VARCHAR2(60)) AS pallet_number,
    CAST(MIN(serial_number) AS VARCHAR2(14)) AS serial_number,
    CAST(MIN(badge_number) AS VARCHAR2(120)) AS badge_number,
    CAST(MIN(purchase_order) AS VARCHAR2(14)) AS purchase_order,
    CAST(MIN(metrology_firmware_version) AS VARCHAR2(60)) AS metrology_firmware_version,
    CAST(MIN(nic_firmware_version) AS VARCHAR2(60)) AS nic_firmware_version
FROM (
    SELECT
        ac.asset_id,
        DECODE(TRIM(ac.asset_id_type_flg), 'W1EI', TRIM(ac.w1_id_value), NULL) AS external_id,
        DECODE(TRIM(ac.asset_id_type_flg), 'W1PN', TRIM(ac.w1_id_value), NULL) AS pallet_number,
        DECODE(TRIM(ac.asset_id_type_flg), 'W1SN', TRIM(ac.w1_id_value), NULL) AS serial_number,
        DECODE(TRIM(ac.asset_id_type_flg), 'W1BN', TRIM(ac.w1_id_value), NULL) AS badge_number,
        DECODE(TRIM(ac.asset_id_type_flg), 'W2PO', TRIM(ac.w1_id_value), NULL) AS purchase_order,
        DECODE(TRIM(ac.asset_id_type_flg), 'W2MF', TRIM(ac.w1_id_value), NULL) AS metrology_firmware_version,
        DECODE(TRIM(ac.asset_id_type_flg), 'W2NF', TRIM(ac.w1_id_value), NULL) AS nic_firmware_version
    FROM cisadm.w1_asset_identifier ac
)
GROUP BY asset_id;

GRANT SELECT ON cisadm.cms_w1_asset_identifier_vw TO cis_read;
GRANT SELECT ON cisadm.cms_w1_asset_identifier_vw TO cis_user;
GRANT SELECT ON cisadm.cms_w1_asset_identifier_vw TO cisread;
GRANT SELECT ON cisadm.cms_w1_asset_identifier_vw TO cisuser;
GRANT SELECT ON cisadm.cms_w1_asset_identifier_vw TO jrs2c2m;

CREATE OR REPLACE SYNONYM cisread.cms_w1_asset_identifier_vw FOR cisadm.cms_w1_asset_identifier_vw;

PROMPT CMS_W1_ASSET_IDENTIFIER_VW created.
