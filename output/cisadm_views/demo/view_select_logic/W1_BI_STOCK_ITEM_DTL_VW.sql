-- SELECT logic for CISADM.W1_BI_STOCK_ITEM_DTL_VW
SELECT
    sid.stock_item_dtl_id,
    sid.sid_class_flg,
    sid.bo_status_cd,
    sid.buyer_cd,
    sid.cost_center_cd,
    sid.max_qty,
    sid.min_qty,
    sid.safety_stock_qty,
    sid.reorder_point,
    sid.reorder_qty,
    sid.auto_reorder_flg,
    sid.abc_class_flg,
    sid.lead_time,
    sid.uop,
    sid.uoi,
    sid.pi_ratio,
    sid.tax_rate_sched_cd,
    b.seqno AS bin_seqno,
    b.bin,
    b.bin_type_flg,
    vl.vendor_loc_id,
    vl.vendor_part_no,
    vl.vendor_pri_flg,
    (select  imfr.w1_manufacturer_cd
    from w1_resrc_type_mfr imfr
    where rownum=1 and imfr.RESRC_TYPE_ID=SID.RESRC_TYPE_ID and imfr.w1_manufacturer_cd= (
    SELECT
            MIN(m.w1_manufacturer_cd)
        FROM
            w1_resrc_type_mfr m
        WHERE
            m.resrc_type_id = sid.resrc_type_id
       )
    )
      as w1_manufacturer_cd,
    (select  imfr.copy_to_po_flg
    from w1_resrc_type_mfr imfr
    where rownum=1 and imfr.RESRC_TYPE_ID=SID.RESRC_TYPE_ID and imfr.w1_manufacturer_cd= (
    SELECT
            MIN(m.w1_manufacturer_cd)
        FROM
            w1_resrc_type_mfr m
        WHERE
            m.resrc_type_id = sid.resrc_type_id
       )
    ) as copy_to_po_flg,
    (select  imfr.manufacturer_part_no
    from w1_resrc_type_mfr imfr
    where rownum=1 and imfr.RESRC_TYPE_ID=SID.RESRC_TYPE_ID and imfr.w1_manufacturer_cd=(
    SELECT
            MIN(m.w1_manufacturer_cd)
        FROM
            w1_resrc_type_mfr m
        WHERE
            m.resrc_type_id = sid.resrc_type_id
       )
    ) as manufacturer_part_no,
    sid.master_stock_item_dtl_id
 
FROM
    w1_stock_item_dtl              sid
    LEFT OUTER JOIN w1_stock_item_dtl_bin          b ON b.stock_item_dtl_id = sid.stock_item_dtl_id
                                               AND b.bin_type_flg = 'W1PR'
    LEFT OUTER JOIN w1_stock_item_dtl_vendor_loc   vl ON vl.stock_item_dtl_id = sid.stock_item_dtl_id
                                                       AND vl.vendor_pri_flg = 'W1PR'
