-- SELECT logic for CISADM.X1_BI_DVC_EVT_VW
select DE.DVC_EVT_ID,
       DE.DVC_EVT_TYPE_CD,
       DE.BO_STATUS_CD,
       DE.BO_STATUS_REASON_CD,
       DE.EXT_EVT_NAME_FLG,
       DE.CRE_DTTM,
       DE.STATUS_UPD_DTTM,
       DE.DVC_EVT_DTTM,
       DE.D1_SPR_CD,
       DE.D1_DEVICE_ID,
       cast('' as char(12))     as MEASR_COMP_ID,
       DS.D1_SP_ID,
       cast(nvl(SP.ID_VALUE, SC.PREM_ID) as char(10)) as PREM_ID,
       SS.SA_ID,
       SA.ACCT_ID,
       PE.PER_ID,
       DE.ILM_DT
 from D1_DVC_EVT DE
 left join (select D1.D1_DEVICE_ID,
                last_value(I1.D1_SP_ID) over (partition by D1.D1_DEVICE_ID order by I1.D1_INSTALL_DTTM) D1_SP_ID
                 from D1_DVC_CFG     D1
           inner join D1_INSTALL_EVT I1 on D1.DEVICE_CONFIG_ID = I1.DEVICE_CONFIG_ID
                            ) DS on DS.D1_DEVICE_ID = DE.D1_DEVICE_ID
 left join D1_SP_IDENTIFIER   SI on SI.D1_SP_ID     = DS.D1_SP_ID and SI.SP_ID_TYPE_FLG = 'D1EI'
 left join D1_SP_IDENTIFIER   SP on SP.D1_SP_ID     = DS.D1_SP_ID and SP.SP_ID_TYPE_FLG = 'D1EP'
 left join (select SP_ID, max(SA_ID) SA_ID from CI_SA_SP S1
             where START_DTTM = (select min(START_DTTM) START_DTTM from CI_SA_SP /* longest active */
                                 where SP_ID = S1.SP_ID and STOP_DTTM is null)
             group by SP_ID)  SS on SS.SP_ID = SI.ID_VALUE
 left join CI_SP              SC on SC.SP_ID        = SS.SP_ID
 left join CI_SA              SA on SA.SA_ID        = SS.SA_ID
 left join CI_ACCT_PER        PE on PE.ACCT_ID      = SA.ACCT_ID and PE.MAIN_CUST_SW = 'Y'
