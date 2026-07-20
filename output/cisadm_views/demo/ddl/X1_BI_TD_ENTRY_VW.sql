CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."X1_BI_TD_ENTRY_VW" ("TD_ENTRY_ID", "TD_TYPE_CD", "ENTRY_STATUS_FLG", "TD_PRIORITY_FLG", "SA_ID", "ACCT_ID", "PER_ID", "PREM_ID", "D1_SP_ID", "D1_DEVICE_ID", "MEASR_COMP_ID", "CONTACT_ID", "US_ID", "ASSET_ID", "TD_CRE_DTTM", "ASSIGNED_DTTM", "COMPLETE_DTTM", "ASSIGNED_TO_USER_ID", "COMPLETE_USER_ID", "UNASSIGNED_TM_MINS", "ASSIGNED_TM_MINS", "COMPLETE_TM_MINS", "MESSAGE_CAT_NBR", "MESSAGE_NBR") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
    tde.td_entry_id,
    tde.td_type_cd,
    tde.entry_status_flg,
    tde.td_priority_flg,
    cast(sa_id as char(10)) sa_id,
    cast(acct_id as char(10)) acct_id ,
    cast(per_id as char(10)) per_id,
    cast(prem_id as char(10)) prem_id,
    cast(d1_sp_id as char(12)) d1_sp_id,
    cast(d1_device_id as char(12)) d1_device_id,
    cast(measr_comp_id as char(12)) measr_comp_id,
    cast(contact_id as char(12)) contact_id,
    cast(us_id as char(12)) us_id,
    cast(asset_id as char(12)) asset_id,
    tde.cre_dttm AS td_cre_dttm,
    tde.assigned_dttm,
    tde.complete_dttm,
    tde.assigned_to AS assigned_to_user_id,
    tde.complete_user_id,
    CASE
        WHEN tde.entry_status_flg = 'O' THEN
            round(current_date - cre_dttm, 2) * 24 * 60
        ELSE
            round(assigned_dttm - cre_dttm, 2) * 24 * 60
    END AS unassigned_tm_mins,
    CASE
        WHEN tde.entry_status_flg = 'W' THEN
            round(current_date - assigned_dttm, 2) * 24 * 60
        WHEN tde.entry_status_flg = 'C' THEN
            round(complete_dttm - assigned_dttm, 2) * 24 * 60
        ELSE
            0
    END AS assigned_tm_mins,
    CASE
        WHEN tde.entry_status_flg = 'C' THEN
            round(complete_dttm - cre_dttm,2) * 24 * 60
         ELSE 0
    END AS complete_tm_mins,
    tde.message_cat_nbr,
    tde.message_nbr
FROM
    ci_td_entry tde
    LEFT OUTER JOIN (
        SELECT
            td_entry_id,
            MIN(sa_id) sa_id,
            MIN(acct_id) acct_id,
            MIN(per_id) per_id,
            MIN(prem_id) prem_id,
            MIN(d1_sp_id) d1_sp_id,
            MIN(d1_device_id) d1_device_id,
            MIN(measr_comp_id) measr_comp_id,
            MIN(contact_id) contact_id,
            MIN(us_id) us_id,
            MIN(asset_id) asset_id
        FROM
            (
                SELECT
                    td.td_entry_id,
                    DECODE(TRIM(fkr.tbl_name), 'CI_SA', tdc.char_val_fk1, NULL) AS sa_id,
                    DECODE(TRIM(fkr.tbl_name), 'CI_ACCT', tdc.char_val_fk1, NULL) AS acct_id,
                    DECODE(TRIM(fkr.tbl_name), 'CI_PER', tdc.char_val_fk1, NULL) AS per_id,
                    DECODE(TRIM(fkr.tbl_name), 'CI_PREM', tdc.char_val_fk1, NULL) AS prem_id,
                    DECODE(TRIM(fkr.tbl_name), 'D1_SP', tdc.char_val_fk1, NULL) AS d1_sp_id,
                    DECODE(TRIM(fkr.tbl_name), 'D1_DVC', tdc.char_val_fk1, NULL) AS d1_device_id,
                    DECODE(TRIM(fkr.tbl_name), 'D1_MEASR_COMP', tdc.char_val_fk1, NULL) AS measr_comp_id,
                    DECODE(TRIM(fkr.tbl_name), 'D1_CONTACT', tdc.char_val_fk1, NULL) AS contact_id,
                   DECODE(TRIM(fkr.tbl_name), 'D1_US', tdc.char_val_fk1, NULL) AS us_id,
                    DECODE(TRIM(fkr.tbl_name), 'W1_ASSET', tdc.char_val_fk1, NULL) AS asset_id
                FROM
                    ci_td_entry       td,
                    ci_td_entry_cha   tdc,
                    ci_char_type      ct,
                    ci_fk_ref         fkr
                WHERE
                    tdc.td_entry_id = td.td_entry_id
                    AND ct.char_type_cd = tdc.char_type_cd
                    AND ct.char_type_flg = 'FKV'
                    AND fkr.fk_ref_cd = ct.fk_ref_cd
                    AND TRIM(fkr.tbl_name) IN (
                        'CI_SA',
                        'CI_ACCT',
                        'CI_PER',
                        'CI_PREM',
                        'D1_SP',
                        'D1_DVC',
                        'D1_MEASR_COMP',
                        'D1_CONTACT',
                        'D1_US',
                        'W1_ASSET'
                    )
            )
        GROUP BY
            td_entry_id
    ) fks ON ( fks.td_entry_id = tde.td_entry_id );
