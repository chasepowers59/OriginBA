-- SELECT logic for CISADM.W1_BI_ASTAVAILWO_VW
SELECT
     asset_id            AS ASSET_ID,
     node_id             AS NODE_ID,
     wo_id               AS WO_ID,
     act_id              AS ACT_ID,
     w1_crew_id          AS W1_CREW_ID,
     event_start         AS WO_CRE_DTTM,
     event_end           AS FINISH_DTTM,
     1                    AS FAILURE_COUNT,
    trunc(in_service_dt) AS IN_SERVICE_DT,
     round((event_end - event_start)* 24 * 60 * 60) AS TOT_DOWNTIME_SEC,
     trunc(acquisition_dt)       AS ACQUISITION_DT,
     decode(useful_life,0,null,nvl2(in_service_dt, round((useful_life - (current_date - in_service_dt))/365,1), null)) AS REMAIN_LIFE_YRS,
     decode(economic_life,0,null,nvl2(in_service_dt, round((economic_life - (current_date - in_service_dt))/365,1), null)) AS ECONOMIC_REMAIN_LIFE_YRS,
     predctd_wear_out_dt AS PREDICT_WEAR_OUT_DT,
     owning_access_grp_cd as owning_access_grp_cd
 FROM
     (
         SELECT
             aa.asset_id,
             aa.node_id,
             wo.wo_id,
             act.act_id,
             act.W1_CREW_ID,
             ast.in_service_dt as in_service_dt,
             ast.acquisition_dt,
             decode(nvl(ast.useful_life,0),0,nvl(asty.useful_life,0),ast.useful_life) * 365 AS useful_life,
             nvl(ast.eco_life,0) * 365 AS economic_life,
             ast.predctd_wear_out_dt,
             nvl2(wo.work_req_id,(select wr.cre_dttm from w1_work_req wr where wr.work_req_id = wo.work_req_id),wo.cre_dttm) AS event_start,
             act.status_upd_dttm AS event_end,
             nvl(ast.owning_access_grp_cd,wo.owning_access_grp_cd) owning_access_grp_cd
         FROM
             w1_wo wo,
             w1_activity act,
             w1_activity_asset aa,
             w1_asset ast,
             w1_asset_type asty
         WHERE act.wo_id = wo.wo_id
           AND aa.act_id = act.act_id
           AND aa.asset_id = ast.asset_id
           and asty.asset_type_cd = ast.asset_type_cd
           AND wo.bo_status_cd IN (
                 'COMPLETED',
                 'CLOSED'
             )
           AND act.bo_status_cd = 'COMPLETE' 
           AND exists
             (select 'x'
              from w1_svc_hist sh,
                   w1_svc_hist_type sht
              where
                  sh.asset_id = aa.asset_id
              AND sh.act_id = act.act_id
              AND sht.svc_hist_type_cd = sh.svc_hist_type_cd
              AND sht.svc_hist_category_flg = 'W1FA'
             )        
     )
 ORDER BY
     asset_id,
     wo_id,
     act_id
