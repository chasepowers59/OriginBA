CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."C1_BI_BILL_DAY_IN_WIN_VW" ("BKT_CONFIG_CD", "SEQ_NUM", "BKT_START_RANGE", "BKT_END_RANGE", "RANGE_DESCR", "BILL_WINDOW_CAT_FLG", "BILL_WINDOW_CAT_DESCR") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
      vl.bkt_config_cd,
      vl.seq_num,
      vl.bkt_start_range,
      vl.bkt_end_range,
      vll.descr   AS range_descr,
      vl.bkt_val_type_cd,
      lv.descr    AS bill_window_cat_descr
  FROM
      f1_bkt_config_val vl
      JOIN f1_bkt_config bk ON bk.bus_obj_cd = 'C1-BillingDayInWindow'
                               AND bk.bkt_config_cd = vl.bkt_config_cd
                               AND bk.bkt_type_cd = 'C1IW'
      JOIN f1_bkt_config_val_l vll ON vll.bkt_config_cd = vl.bkt_config_cd
                                      AND vll.seq_num = vl.seq_num
                                      AND vll.language_cd = 'ENG'
      LEFT OUTER JOIN ci_lookup_val_l lv ON lv.field_name = 'BILL_WINDOW_CAT_FLG'
                                      AND lv.field_value = vl.bkt_val_type_cd
                                      AND lv.language_cd = 'ENG';
