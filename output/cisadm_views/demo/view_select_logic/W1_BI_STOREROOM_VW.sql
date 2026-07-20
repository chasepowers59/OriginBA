-- SELECT logic for CISADM.W1_BI_STOREROOM_VW
SELECT
    a.node_id as STOREROOM,
    a.node_type_cd,
    a.node_dpos_flg,
    a.descr100,
    a.parent_node_id,
    a.address1,
    a.address2,
    a.address3,
    a.address4,
    a.country,
    a.city,
    a.w1_suburb,
    a.state,
    a.postal,
    a.location_class_flg,
    (
        SELECT
            w1_contact_id
        FROM
            w1_node_contact nc
        WHERE
            nc.node_id = a.node_id
            AND nc.node_contact_rel_flg = 'W1MC'
    ) AS w1_main_contact_id,
    (
        SELECT
            w1_contact_id
        FROM
            w1_node_contact nc
        WHERE
            nc.node_id = a.node_id
            AND nc.node_contact_rel_flg = 'W1SV'
    ) AS supervisor_id,
    buyer_cd
FROM
    w1_node a,
    w1_node_type nt
WHERE
    nt.node_type_cd = a.node_type_cd
    and nt.NODE_SUBCLASS_FLG = 'W1IN'
