CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_BI_SPECIFICATION_MODEL_VW" ("SPECIFICATION_CD", "W1_BI_MODEL") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
      specification_cd,
      w1_id_value   AS w1_bi_model
  FROM
      w1_specification_identifier si
  WHERE
      si.specification_id_type_flg = 'W1MD';
