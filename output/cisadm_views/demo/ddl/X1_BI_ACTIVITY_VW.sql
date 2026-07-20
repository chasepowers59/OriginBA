CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."X1_BI_ACTIVITY_VW" ("D1_ACTIVITY_ID", "ACTIVITY_TYPE_CD", "BO_STATUS_CD", "BO_STATUS_REASON_CD", "BO_STATUS_COND_FLG", "ACTIVITY_TYPE_CAT_FLG", "CRE_DTTM", "STATUS_UPD_DTTM", "START_DTTM", "END_DTTM", "EFF_DTTM", "ACT_DUR_SEC", "D1_SPR_CD", "D1_DEVICE_ID", "D1_SP_ID", "D1_SP_TYPE_CD", "FACILITY_ID", "PREM_ID", "SA_ID", "ACCT_ID", "PER_ID", "ILM_DT") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  with DS as (
    select AC.D1_ACTIVITY_ID,
           cast(AD.PK_VALUE1 as varchar2(12)) as D1_DEVICE_ID,
           nvl(DS.D1_SP_ID, cast(AP.PK_VALUE1 as varchar2(12))) D1_SP_ID
     from      D1_ACTIVITY         AC
     left join D1_ACTIVITY_REL_OBJ AP on AP.D1_ACTIVITY_ID = AC.D1_ACTIVITY_ID and AP.MAINT_OBJ_CD = 'D1-SP'        and AP.ACTIVITY_REL_OBJ_TYPE_FLG = 'D1RO'
     left join D1_ACTIVITY_REL_OBJ AD on AD.D1_ACTIVITY_ID = AC.D1_ACTIVITY_ID and AD.MAINT_OBJ_CD = 'D1-DEVICE'    and AD.ACTIVITY_REL_OBJ_TYPE_FLG = 'D1RO'
     left join (select D1.D1_DEVICE_ID,
                    last_value(I1.D1_SP_ID) over (partition by D1.D1_DEVICE_ID order by I1.D1_INSTALL_DTTM) D1_SP_ID
                     from D1_DVC_CFG     D1
               inner join D1_INSTALL_EVT I1 on D1.DEVICE_CONFIG_ID = I1.DEVICE_CONFIG_ID
                                ) DS on DS.D1_DEVICE_ID = AD.PK_VALUE1
), SS as (
    select SP_ID, max(SA_ID) SA_ID
      from CI_SA_SP S1
     where START_DTTM = (select min(START_DTTM) START_DTTM from CI_SA_SP /* longest active */
                          where SP_ID = S1.SP_ID and STOP_DTTM is null)
     group by SP_ID
)
select AC.D1_ACTIVITY_ID,
       AC.ACTIVITY_TYPE_CD,
       AC.BO_STATUS_CD,
       AC.BO_STATUS_REASON_CD,
       BS.BO_STATUS_COND_FLG,
       AT.ACTIVITY_TYPE_CAT_FLG,
       AC.CRE_DTTM,
       AC.STATUS_UPD_DTTM,
       AC.START_DTTM,
       AC.END_DTTM,
       AC.EFF_DTTM,
  case when BS.BO_STATUS_COND_FLG = 'F1FL' then
       round((greatest(AC.CRE_DTTM, AC.STATUS_UPD_DTTM, nvl(AC.END_DTTM, AC.STATUS_UPD_DTTM)) - AC.CRE_DTTM)*24*60*60)
  else round((CURRENT_DATE - AC.CRE_DTTM)*24*60*60) end as ACT_DUR_SEC,
       cast(AR.PK_VALUE1 as varchar2(30)) as D1_SPR_CD,
       DS.D1_DEVICE_ID,
       DS.D1_SP_ID,
       ST.D1_SP_TYPE_CD,
       SF.FACILITY_ID,
       cast(nvl(PI.ID_VALUE, SC.PREM_ID) as char(10)) as PREM_ID,
       SS.SA_ID,
       SA.ACCT_ID,
       PE.PER_ID,
       AC.ILM_DT
 from      D1_ACTIVITY         AC
inner join                     DS  on DS.D1_ACTIVITY_ID = AC.D1_ACTIVITY_ID
inner join D1_ACTIVITY_TYPE    AT  on AT.ACTIVITY_TYPE_CD = AC.ACTIVITY_TYPE_CD
inner join F1_BUS_OBJ          BO  on BO.BUS_OBJ_CD     = AC.BUS_OBJ_CD
inner join F1_BUS_OBJ_STATUS   BS  on BS.BUS_OBJ_CD     = BO.LIFE_CYCLE_BO_CD  and BS.BO_STATUS_CD   = AC.BO_STATUS_CD
 left join D1_ACTIVITY_REL_OBJ AR  on AR.D1_ACTIVITY_ID = AC.D1_ACTIVITY_ID    and AR.MAINT_OBJ_CD   = 'D1-SVCPROVDR' and AR.ACTIVITY_REL_OBJ_TYPE_FLG = 'D1RC'
 left join D1_SP_IDENTIFIER    SI  on SI.D1_SP_ID       = DS.D1_SP_ID          and SI.SP_ID_TYPE_FLG = 'D1EI'
 left join D1_SP_IDENTIFIER    PI  on PI.D1_SP_ID       = DS.D1_SP_ID          and PI.SP_ID_TYPE_FLG = 'D1EP'
 left join D1_SP               ST  on ST.D1_SP_ID       = DS.D1_SP_ID
 left join D1_SP_FACILITY      SF  on SF.D1_SP_ID       = DS.D1_SP_ID          and SF.FACILITY_REL_TYPE_FLG = 'D1CD'
 left join                     SS  on SS.SP_ID          = SI.ID_VALUE
 left join CI_SP               SC  on SC.SP_ID          = SS.SP_ID
 left join CI_SA               SA  on SA.SA_ID          = SS.SA_ID
 left join CI_ACCT_PER         PE  on PE.ACCT_ID        = SA.ACCT_ID           and PE.MAIN_CUST_SW = 'Y';
