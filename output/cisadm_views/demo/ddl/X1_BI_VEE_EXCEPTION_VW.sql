CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."X1_BI_VEE_EXCEPTION_VW" ("VEE_EXCP_ID", "EXCP_TYPE_CD", "EXCP_SEVERITY_FLG", "MESSAGE_CAT_NBR", "MESSAGE_NBR", "MESSAGE_TEXT", "VEE_GRP_CD", "VEE_RULE_CD", "EXCP_CRE_DTTM", "EXCP_STATUS_DTTM", "OPEN_CLOSE_FLG", "TD_ENTRY_ID", "TD_TYPE_CD", "INIT_MSRMT_DATA_ID", "MEASR_COMP_ID", "D1_DEVICE_ID", "D1_SPR_CD", "MDM_SP_ID", "CCB_SP_ID", "PREM_ID", "SA_ID", "PER_ID", "CCB_ACCT_ID", "CCB_BILL_CYC_CD", "US_ID", "CSTMR_NM", "INSTALL_EVT_ID", "ILM_DT") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  select
    E.VEE_EXCP_ID  ,
    E.EXCP_TYPE_CD   ,
    E.EXCP_SEVERITY_FLG ,
    E.MESSAGE_CAT_NBR ,
    E.MESSAGE_NBR ,
    null MESSAGE_TEXT,
    E.VEE_GRP_CD  ,
    E.VEE_RULE_CD  ,
    E.CRE_DTTM as EXCP_CRE_DTTM ,
    E.STATUS_UPD_DTTM as EXCP_STATUS_DTTM ,
    E.OPEN_CLOSE_FLG ,
    null TD_ENTRY_ID,
    null TD_TYPE_CD,
    IMDC.INIT_MSRMT_DATA_ID ,
    MC.MEASR_COMP_ID ,
    D.D1_DEVICE_ID ,
    D.D1_SPR_CD ,
    SP.D1_SP_ID as MDM_SP_ID,
    SS.SP_ID CCB_SP_ID,
    cast(nvl(SPID.ID_VALUE, SC.PREM_ID) as char(10)) as PREM_ID,
    SS.SA_ID,
    PE.PER_ID,
    SA.ACCT_ID CCB_ACCT_ID,
    MBC.D1_BILL_CYC_CD CCB_BILL_CYC_CD,
    USSP.US_ID,
    CNT.NAME_VALUE as CSTMR_NM,
    IE.INSTALL_EVT_ID,
    E.ILM_DT
from
    D1_VEE_EXCP E
    left join D1_IMD_CTRL IMDC on  E.INIT_MSRMT_DATA_ID = IMDC.INIT_MSRMT_DATA_ID
    left join D1_MEASR_COMP MC          on IMDC.IMD_CTRL_MC_ID = MC.MEASR_COMP_ID
    left join D1_DVC_CFG DC             on MC.DEVICE_CONFIG_ID = DC.DEVICE_CONFIG_ID
    left join D1_DVC D                  on DC.D1_DEVICE_ID = D.D1_DEVICE_ID
    left join D1_INSTALL_EVT IE         on DC.DEVICE_CONFIG_ID = IE.DEVICE_CONFIG_ID
    left join D1_SP SP                  on IE.D1_SP_ID = SP.D1_SP_ID
    left join D1_US_SP USSP             on SP.D1_SP_ID = USSP.D1_SP_ID
    left join D1_US_CONTACT USC         on USSP.US_ID = USC.US_ID
    left join D1_CONTACT_NAME CNT       on CNT.CONTACT_ID = USC.CONTACT_ID
    left join D1_MSRMT_CYC_BILL_CYC MBC on SP.MSRMT_CYC_CD = MBC.MSRMT_CYC_CD
    left join D1_SP_IDENTIFIER SPI      on SP.D1_SP_ID = SPI.D1_SP_ID
                                        and SPI.SP_ID_TYPE_FLG = 'D1EI'
    left join D1_SP_IDENTIFIER SPID      on SP.D1_SP_ID = SPID.D1_SP_ID
                                        and SPID.SP_ID_TYPE_FLG = 'D1EP'
 left join (select SP_ID, max(SA_ID) SA_ID from CI_SA_SP S1
             where START_DTTM = (select min(START_DTTM) START_DTTM from CI_SA_SP /* longest active */
                                 where SP_ID = S1.SP_ID and STOP_DTTM is null)
             group by SP_ID)  SS on SS.SP_ID = SPI.ID_VALUE
 left join CI_SP              SC on SC.SP_ID        = SS.SP_ID
 left join CI_SA              SA on SA.SA_ID        = SS.SA_ID
 left join CI_ACCT_PER        PE on PE.ACCT_ID      = SA.ACCT_ID and PE.MAIN_CUST_SW = 'Y';
