-- SELECT logic for CISADM.X1_BI_USG_EXCEPTION_VW
select
  E.USAGE_EXCP_ID,
  E.USAGE_EXCP_TYPE_CD as USG_EXCP_TYPE_CD,
  E.EXCP_SEVERITY_FLG,
  E.OPEN_CLOSE_FLG,
  E.MESSAGE_CAT_NBR,
  E.MESSAGE_NBR,
  MSG.MESSAGE_TEXT,
  E.USG_GRP_CD,
  E.USG_RULE_CD,
  E.CRE_DTTM           as EXCP_CRE_DTTM,
  E.STATUS_UPD_DTTM    as EXCP_STATUS_DTTM,
  null                 as TD_ENTRY_ID,
  null                 as TD_TYPE_CD,
  E.D1_USAGE_ID,
  USSP.US_ID,
  CNT.NAME_VALUE       as CSTMR_NM,
  SP.D1_SP_ID          as MDM_SP_ID,
  CSP.SP_ID            as CCB_SP_ID,
  CSP.PREM_ID          as PREM_ID,
  SA.SA_ID,
  SA.SA_TYPE_CD,
  DIV.DESCR            as CIS_DIV,
  ACP.ACCT_ID          as CCB_ACC_ID,
  ACP.PER_ID,
  CBC.BILL_CYC_CD      as CCB_BILL_CYC_CD,
  E.ILM_DT
from
  D1_USAGE_EXCP E
  left join D1_USAGE              USG on USG.D1_USAGE_ID = E.D1_USAGE_ID
  left join (select distinct U1.US_ID,
                last_value(U1.D1_SP_ID) over (partition by U1.US_ID order by U1.START_DTTM) as D1_SP_ID
               from D1_US_SP U1) USSP on USG.US_ID = USSP.US_ID
  left join D1_US_CONTACT         USC on USSP.US_ID = USC.US_ID
  left join D1_CONTACT_NAME       CNT on CNT.CONTACT_ID = USC.CONTACT_ID
  left join D1_SP                  SP on USSP.D1_SP_ID = SP.D1_SP_ID
  left join D1_MSRMT_CYC_BILL_CYC MBC on SP.MSRMT_CYC_CD = MBC.MSRMT_CYC_CD
  left join CI_BILL_CYC           CBC on MBC.D1_BILL_CYC_CD = CBC.BILL_CYC_CD
  left join D1_SP_IDENTIFIER      SPI on SP.D1_SP_ID = SPI.D1_SP_ID and SPI.SP_ID_TYPE_FLG = 'D1EI'
  left join D1_SP_IDENTIFIER     SPID on SP.D1_SP_ID = SPID.D1_SP_ID and SPID.SP_ID_TYPE_FLG = 'D1EP'
  left join (select SP_ID, max(SA_ID) SA_ID from CI_SA_SP S1
              where START_DTTM = (select min(START_DTTM) START_DTTM from CI_SA_SP /* longest active */
                                  where SP_ID = S1.SP_ID and STOP_DTTM is null)
              group by SP_ID)      SS on SS.SP_ID = SPI.ID_VALUE
  left join CI_SP                 CSP on SPI.ID_VALUE = CSP.SP_ID
  left join CI_SA                  SA on SS.SA_ID = SA.SA_ID
  left join CI_CIS_DIVISION_L     DIV on SA.CIS_DIVISION = DIV.CIS_DIVISION and DIV.LANGUAGE_CD  = 'ENG'
  left join CI_ACCT_PER           ACP on SA.ACCT_ID = ACP.ACCT_ID and ACP.MAIN_CUST_SW = 'Y'
  left join CI_MSG_L              MSG on E.MESSAGE_CAT_NBR = MSG.MESSAGE_CAT_NBR
                                     and E.MESSAGE_NBR = MSG.MESSAGE_NBR and MSG.LANGUAGE_CD  = 'ENG'
