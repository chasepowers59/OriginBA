-- SELECT logic for CISADM.W1_BI_STOCK_ITEM_VW
SELECT
    rt.resrc_type_id   AS stock_item_id,
    rt.bo_status_cd,
    rti.w1_id_value    AS stock_item_code,
    (rti.w1_id_value || ' (' || rtl.descr100 || ')') as stock_information,
    rtl.descr100,
    rtl.descrlong,
    rt.stock_cat_flg,
    rt.hazardous_flg,
    rt.hazard_type_flg,
    rt.lot_managed_flg,
    rt.shelf_life,
    rt.capital_spare_flg,
    rt.trackable_flg,
    rt.repairable_flg,
    rt.truck_stock_flg,
    rt.acpt_on_rcpt_flg,
    rt.purchase_cmdty_cd,
    rt.do_not_sub_flg,
    rt.cmdty_cat_cd,
    rt.cmdty_name_cd,
    rt.cmdty_type_cd,
    rt.inventory_expense_cd,
    rt.expense_cd,
    rt.unit_price,
    rt.add_to_bom_flg
FROM
    w1_resrc_type              rt,
    w1_resrc_type_l            rtl,
    w1_resrc_type_identifier   rti
WHERE
    rt.w1_resrc_class_flg = 'W1MT'
    AND rtl.resrc_type_id = rt.resrc_type_id
    AND rtl.language_cd = 'ENG'
    AND rti.resrc_type_id = rt.resrc_type_id
    AND rti.resrc_type_id_type_flg = 'W1RC'
