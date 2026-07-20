-- SELECT logic for CISADM.W1_BI_SPECIFICATION_MODEL_VW
SELECT
      specification_cd,
      w1_id_value   AS w1_bi_model
  FROM
      w1_specification_identifier si
  WHERE
      si.specification_id_type_flg = 'W1MD'
