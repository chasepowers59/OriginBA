CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_BI_SERVICEHISTORY_VW" ("SVC_HIST_ID", "SVC_HIST_TYPE_CD", "SVC_HIST_CATEGORY_FLG", "BO_STATUS_CD", "BO_STATUS_REASON_CD", "SVC_HIST_CRE_DTTM", "END_DTTM", "SVC_HIST_STATUS_UPD_DTTM", "ASSET_ID", "IN_SERVICE_DT", "ACQUISITION_DT", "PREDCTD_WEAR_OUT_DT", "NODE_ID", "ACT_ID", "WO_ID", "FAILURE_MODE_CD", "FAILURE_TYPE_CD", "FAILURE_REPAIR_CD", "FAILURE_COMP_CD", "USER_ID", "EFF_DTTM", "ASSET_SCORE_FLG", "INSPECTED_BY_USER", "ANNIVERSARY_DT", "ANNIVERSARY_VALUE", "PERMIT_ID", "MAINT_SCHED_ID", "MAINT_TRIGGER_ID", "OWNING_ACCESS_GRP_CD", "SVC_HIST_CNT") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
     sh.svc_hist_id as SVC_HIST_ID,
     sh.svc_hist_type_cd as SVC_HIST_TYPE_CD,
     sht.svc_hist_category_flg as SVC_HIST_CATEGORY_FLG,
     sh.bo_status_cd as BO_STATUS_CD,
     sh.bo_status_reason_cd as BO_STATUS_REASON_CD,
     sh.cre_dttm as SVC_HIST_CRE_DTTM,
     sh.end_dttm as END_DTTM,
     sh.status_upd_dttm as SVC_HIST_STATUS_UPD_DTTM,
     sh.asset_id as ASSET_ID,
     trunc(ast.in_service_dt) as IN_SERVICE_DT,
     ast.acquisition_dt as ACQUISITION_DT,
     ast.predctd_wear_out_dt as PREDCTD_WEAR_OUT_DT,
     sh.node_id as NODE_ID,
     ac.act_id as ACT_ID,
     ac.wo_id as WO_ID,
     sh.failure_mode_cd as FAILURE_MODE_CD,
     sh.failure_type_cd as FAILURE_TYPE_CD,
     sh.failure_repair_cd as FAILURE_REPAIR_CD,
     sh.failure_comp_cd as FAILURE_COMP_CD,
     sh.user_id as USER_ID,
     sh.eff_dttm as EFF_DTTM,
     sh.asset_score_flg as ASSET_SCORE_FLG,
     sh.inspected_by_user as INSPECTED_BY_USER,
     sh.anniversary_dt as ANNIVERSARY_DT,
     sh.anniversary_value as ANNIVERSARY_VALUE,
     sh.permit_id as PERMIT_ID,
     sh.maint_sched_id as MAINT_SCHED_ID,
     sh.maint_trigger_id as MAINT_TRIGGER_ID,
     nvl(ast.owning_access_grp_cd, sh.owning_access_grp_cd) as OWNING_ACCESS_GRP_CD,
     1 as SVC_HIST_CNT
 FROM
    w1_svc_hist sh
 inner join w1_svc_hist_type sht on sht.svc_hist_type_cd = sh.svc_hist_type_cd
 left join w1_activity ac on ac.act_id = sh.act_id
 left join w1_asset ast on ast.asset_id = sh.asset_id;
