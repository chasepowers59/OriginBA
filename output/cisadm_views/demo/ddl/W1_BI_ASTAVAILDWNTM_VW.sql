CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_BI_ASTAVAILDWNTM_VW" ("ASSET_ID", "NODE_ID", "WO_ID", "ACT_ID", "DOWNTIME_SVC_HIST_ID", "W1_CREW_ID", "DOWNTIME_RSN", "DOWNTIME_START_DTTM", "DOWNTIME_END_DTTM", "FAILURE_COUNT", "IN_SERVICE_DT", "TOT_DOWNTIME_SEC", "ACQUISITION_DT", "WO_CRE_DTTM", "FINISH_DTTM", "PREDCTD_WEAR_OUT_DT", "OWNING_ACCESS_GRP_CD") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
    asset_id AS ASSET_ID,
    node_id AS NODE_ID,
    wo_id AS WO_ID,
    act_id AS ACT_ID,
    svc_hist_id AS DOWNTIME_SVC_HIST_ID,
    w1_crew_id AS W1_CREW_ID,
    reason AS DOWNTIME_RSN,
    event_start AS DOWNTIME_START_DTTM,
    nvl(event_end_dt, nvl2(fail_svc_hist_id, (select z.end_dttm from w1_svc_hist z where z.svc_hist_id = fail_svc_hist_id), wo_end)) AS DOWNTIME_END_DTTM,
    1 AS FAILURE_COUNT,
    trunc(in_service_dt) AS IN_SERVICE_DT,
    ROUND(((nvl(event_end_dt, nvl2(fail_svc_hist_id, (select z.end_dttm from w1_svc_hist z where z.svc_hist_id = fail_svc_hist_id), wo_end)) - event_start)*24*60*60),0) AS TOT_DOWNTIME_SEC,
    acquisition_dt as ACQUISITION_DT,
    wo_cre_dt as WO_CRE_DTTM,
    wo_end as FINISH_DTTM,
    predctd_wear_out_dt as PREDCTD_WEAR_OUT_DT,
    owning_access_grp_cd as OWNING_ACCESS_GRP_CD
FROM
  ( SELECT
       aa.asset_id,
       aa.node_id,
       wo.wo_id,
       sh.act_id,
       sh.svc_hist_id svc_hist_id,
       -- pick a failure SH if any
       (select min(shf.svc_hist_id)
        from w1_svc_hist shf,
             w1_svc_hist_type shtf
        where shf.asset_id = aa.asset_id
        AND shf.act_id = aa.act_id
        AND shtf.svc_hist_type_cd = shf.svc_hist_type_cd
        AND shtf.svc_hist_category_flg = 'W1FA') fail_svc_hist_id,
        act.W1_CREW_ID,
        shc.char_val reason,
        ast.in_service_dt as in_service_dt,
        -- downtime start date is in CLOB
        to_date(regexp_substr(sh.bo_data_area,'<startDateTime>([^<]*)</startDateTime>',1,1,'i',1),'YYYY-MM-DD-HH24.MI.SS') event_start,
        sh.end_dttm event_end_dt,
        decode(trim(wo.bo_status_cd), 'COMPLETED',wo.status_upd_dttm,
                 (select max(lg.log_dttm) from w1_wo_log lg where lg.wo_id = wo.wo_id and lg.bo_status_cd = 'COMPLETED')) as wo_end,
        nvl2(wo.work_req_id,(select wr.cre_dttm from w1_work_req wr where wr.work_req_id = wo.work_req_id),wo.cre_dttm) as wo_cre_dt,
        ast.acquisition_dt,
        ast.predctd_wear_out_dt,
        nvl(ast.owning_access_grp_cd, sh.owning_access_grp_cd) owning_access_grp_cd
    FROM
        w1_wo wo,
        w1_activity act,
        w1_activity_asset aa,
        w1_svc_hist sh,
        w1_svc_hist_type sht,
       (select distinct svc_hist_id, char_val  from w1_svc_hist_char  where char_type_cd = 'W1-DTRSN' AND srch_char_val = 'NPL') shc,
        w1_asset ast
     WHERE
        act.wo_id = wo.wo_id
        AND aa.act_id = act.act_id
        AND wo.bo_status_cd IN ( 'COMPLETED', 'CLOSED' )
        AND act.bo_status_cd = 'COMPLETE'
        AND sh.asset_id = aa.asset_id
        and sh.act_id = act.act_id
        AND sht.svc_hist_type_cd = sh.svc_hist_type_cd
        AND sht.svc_hist_category_flg = 'W1DT'
        AND shc.svc_hist_id = sh.svc_hist_id
        AND aa.asset_id = ast.asset_id
 );
