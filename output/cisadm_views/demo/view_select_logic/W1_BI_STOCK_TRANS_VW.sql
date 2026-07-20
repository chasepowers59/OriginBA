-- SELECT logic for CISADM.W1_BI_STOCK_TRANS_VW
SELECT
    st.stock_trans_id,
    st.stock_item_dtl_id,
    sid.resrc_type_id    AS stock_item_id,
    sid.node_id          AS storeroom,
    st.w1_trans_dt,
    
    case
        when sid.sid_class_flg  ='W1IT' THEN
          0
        ELSE
          st.inventory_qty
     END AS  total_inventory_on_hand_qty,  
    st.on_demand_qty     AS total_on_demand_qty,
    st.on_order_qty      AS total_on_order_qty,
    st.in_transfer_qty   AS total_in_transfer_qty,
    st.in_receipt_qty    AS total_in_receipt_qty,
    st.reserved_qty      AS total_reserved_qty,
     
    case
        when sid.sid_class_flg  ='W1IT' THEN
          0
        ELSE
          st.inventory_qty * st.unit_price
     END AS  total_inventory_cost,      
    st.unit_price,
    st.parent_mo_cd      AS initiated_by_mo_cd,
    CASE
        WHEN st.parent_mo_cd = 'W1-MATISSLIN' THEN
            st.parent_pk1
        ELSE
            NULL
    END AS mat_issue_line_id,
    CASE
        WHEN st.parent_mo_cd = 'W1-MATRTNLIN' THEN
            st.parent_pk1
        ELSE
            NULL
    END AS mat_ret_line_id,
    CASE
        WHEN st.parent_mo_cd = 'W1-PILINE' THEN
            st.parent_pk1
        ELSE
            NULL
    END AS pi_cnt_line_id,
    CASE
        WHEN st.parent_mo_cd = 'W1-INVADJ' THEN
            st.parent_pk1
        ELSE
            NULL
    END AS inv_adj_id,
    CASE
        WHEN st.parent_mo_cd = 'W1-ACPTLINE' THEN
            st.parent_pk1
        ELSE
            NULL
    END AS accept_line_id,
    CASE
        WHEN st.parent_mo_cd = 'W1-RTNLINE' THEN
            st.parent_pk1
        ELSE
            NULL
    END AS rtn_line_id,
    CASE
        WHEN st.parent_mo_cd = 'W1-POLINE' THEN
            st.parent_pk1
        ELSE
            NULL
    END AS po_line_id,
    SIBLING_MO_CD  as REQUESTED_BY_MO_CD,
    sid.owning_access_grp_cd,
    1 AS STOCK_TRANS_CNT
FROM
    w1_stock_trans      st,
    w1_stock_item_dtl   sid
WHERE
    st.st_rel_flg = 'W1YS'
    AND sid.stock_item_dtl_id = st.stock_item_dtl_id
    and sid.sid_class_flg in ('W1IN','W1IT','W1IL','W1SL')
