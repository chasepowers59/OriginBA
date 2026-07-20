-- SELECT logic for CISADM.CI_ROOT_OBJ_VW
SELECT
RO.ROOT_OBJ_ID,
RO.ENV_REF_CD,
RO.MAINT_OBJ_CD,
RO.ROOT_ACTION_FLG,
RO.ROOT_STATUS_FLG,
RO.VERSION,
RO.BATCH_CD,
RO.BATCH_NBR,
  (select RP.field_val from ci_root_obj_pk RP where RP.root_obj_id = RO.root_obj_id and seq_num = 1) as fld_val1,
  (select RP.field_val from ci_root_obj_pk RP where RP.root_obj_id = RO.root_obj_id and seq_num = 2) as  fld_val2,
  (select RP.field_val from ci_root_obj_pk RP where RP.root_obj_id = RO.root_obj_id and seq_num = 3)  as fld_val3,
  (select RP.field_val from ci_root_obj_pk RP where RP.root_obj_id = RO.root_obj_id and seq_num = 4)  as fld_val4,
  (select RP.field_val from ci_root_obj_pk RP where RP.root_obj_id = RO.root_obj_id and seq_num = 5)  as fld_val5,
  (select RP.field_val from ci_root_obj_pk RP where RP.root_obj_id = RO.root_obj_id and seq_num = 6)  as fld_val6,
  (select RP.field_val from ci_root_obj_pk RP where RP.root_obj_id = RO.root_obj_id and seq_num = 7)  as fld_val7,
  (select RP.field_val from ci_root_obj_pk RP where RP.root_obj_id = RO.root_obj_id and seq_num = 8)  as fld_val8,
  (select RP.field_val from ci_root_obj_pk RP where RP.root_obj_id = RO.root_obj_id and seq_num = 9)  as fld_val9,
  (select RP.field_val from ci_root_obj_pk RP where RP.root_obj_id = RO.root_obj_id and seq_num = 10)  as fld_val10
from ci_root_obj RO

 
 
 
 
