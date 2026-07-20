-- SELECT logic for CISADM.W1_BI_STOCK_ITEM_DTLS_F_VW
SELECT
    sid.stock_item_dtl_id,
    sid.node_id         AS storeroom,
    sid.resrc_type_id   AS stock_item_id,
    nvl(st.total_inventory_cost, 0) as total_inventory_cost,
    nvl(st.total_inventory_on_hand_qty, 0) as total_inventory_on_hand_qty,
    CASE
        WHEN total_inventory_on_hand_qty <= 0 THEN
            1
        ELSE
            0
    END AS total_inv_out_stock_cnt,
    nvl(st.total_reserved_qty, 0) as total_reserved_qty,
    nvl(st.total_on_demand_qty, 0) as total_on_demand_qty,
    nvl(st.total_on_order_qty, 0) as total_on_order_qty,
    nvl(st.total_in_transfer_qty, 0) as total_in_transfer_qty,
    nvl(st.total_in_receipt_qty, 0) as total_in_receipt_qty,
    nvl(materialretun.total_pend_ret_qty, 0) as total_pend_ret_qty,
    nvl(st.total_inventory_available_qty, 0) as total_inventory_available_qty,
    CASE
        WHEN sid.sid_class_flg IN (
            'W1IN',
            'W1IT',
            'W1IL'
        )
             AND st.total_inventory_available_qty < sid.safety_stock_qty THEN
            1
        ELSE
            0
    END AS si_below_safety_stock_cnt,
    CASE
        WHEN sid.sid_class_flg IN (
            'W1IN',
            'W1IT',
            'W1IL'
        )
             AND st.total_inventory_available_qty < sid.min_qty THEN
            1
        ELSE
            0
    END AS si_below_min_qty_cnt,
    CASE
        WHEN sid.sid_class_flg IN (
            'W1IN',
            'W1IT',
            'W1IL'
        )
             AND st.total_inventory_available_qty < sid.reorder_point THEN
            1
        ELSE
            0
    END AS si_below_reorder_pt_cnt,
    sid.owning_access_grp_cd,
    1 AS stock_item_dtl_cnt
FROM
    w1_stock_item_dtl   sid,
    (
        SELECT
            stock_item_dtl_id,
            SUM(total_inventory_on_hand_qty) AS total_inventory_on_hand_qty,
            SUM(total_inventory_cost) AS total_inventory_cost,
            SUM(total_on_demand_qty) AS total_on_demand_qty,
            SUM(total_on_order_qty) AS total_on_order_qty,
            SUM(total_in_transfer_qty) AS total_in_transfer_qty,
            SUM(total_in_receipt_qty) AS total_in_receipt_qty,
            SUM(total_reserved_qty) AS total_reserved_qty,
            ( SUM(total_inventory_on_hand_qty) + SUM(total_on_order_qty) + SUM(total_in_receipt_qty) + SUM(total_in_transfer_qty)
            ) - ( SUM(total_on_demand_qty) + SUM(total_reserved_qty) ) AS total_inventory_available_qty
        FROM
            (
                (
              -- Considering all SIDs except inv tracked for all quanities
                 SELECT
                    st1.stock_item_dtl_id,
                    SUM(inventory_qty) AS total_inventory_on_hand_qty,
                    SUM(st1.inventory_qty * st1.unit_price) AS total_inventory_cost,
                    SUM(st1.on_demand_qty) AS total_on_demand_qty,
                    SUM(st1.on_order_qty) AS total_on_order_qty,
                    SUM(st1.in_transfer_qty) AS total_in_transfer_qty,
                    SUM(st1.in_receipt_qty) AS total_in_receipt_qty,
                    SUM(st1.reserved_qty) AS total_reserved_qty
                FROM
                    w1_stock_trans      st1,
                    w1_stock_item_dtl   invsid
                WHERE
                    st1.st_rel_flg = 'W1YS'
                    AND invsid.stock_item_dtl_id = st1.stock_item_dtl_id
                    AND invsid.sid_class_flg != 'W1IT'
                GROUP BY
                    st1.stock_item_dtl_id
                )
                UNION
                (
                -- Considering only master SIDs of on hand quanities i.e lot managed sids only
                 SELECT
                    sidm.stock_item_dtl_id,
                    SUM(inventory_qty) total_inventory_on_hand_qty,
                    SUM(st2.inventory_qty * st2.unit_price) total_inventory_cost,
                    0 AS total_on_demand_qty,
                    0 AS total_on_order_qty,
                    SUM(in_transfer_qty) AS total_in_transfer_qty,
                    0 AS total_in_receipt_qty,
                    0 AS total_reserved_qty
                FROM
                    w1_stock_item_dtl   sid1,
                    w1_stock_trans      st2,
                    w1_stock_item_dtl   sidm
                WHERE
                    sid1.master_stock_item_dtl_id = sidm.stock_item_dtl_id
                    AND st2.stock_item_dtl_id = sid1.stock_item_dtl_id
                    AND st2.st_rel_flg = 'W1YS'
                GROUP BY
                    sidm.stock_item_dtl_id
                )
                UNION
                (
                -- Considering only inventory tracked SIDs for calculation of on hand quanities
                 SELECT
                    sid.stock_item_dtl_id,
                    COUNT(1) total_inventory_on_hand_qty,
                    SUM(ast.unit_price) total_inventory_cost,
                    0 AS total_on_demand_qty,
                    0 AS total_on_order_qty,
                    0 AS total_in_transfer_qty,
                    0 AS total_in_receipt_qty,
                    0 AS total_reserved_qty
                 --, 0 as total_pend_ret_qty
                FROM
                    w1_asset            ast,
                    w1_specification    spec,
                    w1_asset_node       an,
                    w1_stock_item_dtl   sid
                WHERE
                    spec.resrc_type_id = sid.resrc_type_id
                    AND ast.specification_cd = spec.specification_cd
                    AND an.asset_id = ast.asset_id
                    AND an.curr_node_id = sid.node_id
                    AND an.asset_dpos_flg = 'NI-INSTORE'
                GROUP BY
                    sid.stock_item_dtl_id
                )
                UNION
                (
              -- Considering only inv tracked SIDs
                 SELECT
                    st1.stock_item_dtl_id,
                    0 AS total_inventory_on_hand_qty,
                    0 AS total_inventory_cost,
                    SUM(st1.on_demand_qty) AS total_on_demand_qty,
                    SUM(st1.on_order_qty) AS total_on_order_qty,
                    SUM(st1.in_transfer_qty) AS total_in_transfer_qty,
                    SUM(st1.in_receipt_qty) AS total_in_receipt_qty,
                    SUM(st1.reserved_qty) AS total_reserved_qty
                FROM
                    w1_stock_trans      st1,
                    w1_stock_item_dtl   invtrackedsid
                WHERE
                    st1.st_rel_flg = 'W1YS'
                    AND invtrackedsid.stock_item_dtl_id = st1.stock_item_dtl_id
                    AND invtrackedsid.sid_class_flg = 'W1IT'
                GROUP BY
                    st1.stock_item_dtl_id
                )
            )
        GROUP BY
            stock_item_dtl_id
    ) st,
    (
        ( SELECT
            mt.stock_item_dtl_id,
            SUM(mt.return_qty) AS total_pend_ret_qty
        FROM
           -- w1_stock_trans    st111,
            w1_mat_ret_line   mt
        WHERE
           -- mt.mat_ret_line_id = st111.parent_pk1
           -- AND st111.parent_mo_cd = 'W1-MATRTNLIN'
            --AND
            mt.bo_status_cd = 'CREATED'
        GROUP BY
            mt.stock_item_dtl_id
        )
        UNION
        ( SELECT
            mastersid.master_stock_item_dtl_id,
            SUM(mt.return_qty) AS total_pend_ret_qty
        FROM
            --w1_stock_trans      st111,
            w1_mat_ret_line     mt,
            w1_stock_item_dtl   mastersid
        WHERE
          --  mt.mat_ret_line_id = st111.parent_pk1
            -- AND st111.parent_mo_cd = 'W1-MATRTNLIN' AND
             mt.bo_status_cd = 'CREATED'
             and mt.stock_item_dtl_id=mastersid.stock_item_dtl_id
            --AND mastersid.stock_item_dtl_id = st111.stock_item_dtl_id
            AND mastersid.master_stock_item_dtl_id IS NOT NULL
        GROUP BY
            mastersid.master_stock_item_dtl_id
        )
    ) materialretun,
    w1_resrc_type       si
WHERE
    sid.stock_item_dtl_id = st.stock_item_dtl_id (+)
    AND si.resrc_type_id = sid.resrc_type_id(+)
    AND sid.stock_item_dtl_id = materialretun.stock_item_dtl_id (+)
    AND sid.sid_class_flg IN (
        'W1IN',
        'W1IT',
        'W1IL',
        'W1SL'
    )
