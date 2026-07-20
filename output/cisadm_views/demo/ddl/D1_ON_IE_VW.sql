CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."D1_ON_IE_VW" ("NT_XID_CD", "EXT_PK_VALUE1", "ADHOC_CHAR_VAL", "PK_VALUE1") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
char_type_cd AS nt_xid_cd,
srch_char_val AS ext_pk_value1,
adhoc_char_val as adhoc_char_val,
install_evt_id AS pk_value1
FROM D1_INSTALL_EVT_CHAR;
