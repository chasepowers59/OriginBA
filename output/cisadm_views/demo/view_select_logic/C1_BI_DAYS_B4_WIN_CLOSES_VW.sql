-- SELECT logic for CISADM.C1_BI_DAYS_B4_WIN_CLOSES_VW
SELECT
      vl.bkt_config_cd,
      vl.seq_num,
      vl.bkt_start_range,
      vl.bkt_end_range,
      vll.descr   AS range_descr
  FROM
      f1_bkt_config_val vl
      JOIN f1_bkt_config bk ON bk.bus_obj_cd = 'C1-DaysBeforeBillWindowCloses'
                               AND bk.bkt_config_cd = vl.bkt_config_cd
                               AND bk.bkt_type_cd = 'C1OP'
      JOIN f1_bkt_config_val_l vll ON vll.bkt_config_cd = vl.bkt_config_cd
                                      AND vll.seq_num = vl.seq_num
                                      AND vll.language_cd = 'ENG'
