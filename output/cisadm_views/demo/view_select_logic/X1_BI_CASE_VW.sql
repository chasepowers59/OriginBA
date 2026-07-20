-- SELECT logic for CISADM.X1_BI_CASE_VW
select CA.CASE_ID, CA.CASE_TYPE_CD, CA.CASE_STATUS_CD,
     ACCT_ID, PER_ID, PREM_ID , CA.USER_ID,
     CRE_DTTM AS CASE_CRE_DTTM, CASE_COND_FLG,CLOSED_DTTM,
     CA.ILM_DT, CA.ILM_ARCH_SW,
 CASE
       when CLOSED_DTTM is null  then round((current_date -  cre_dttm)*24*60,2)
       else round((closed_dttm -  cre_dttm)*24*60,2)
     END as CASE_DUR
from CI_CASE CA
inner join
    (select C1.CASE_ID, max(CL.LOG_DTTM) CRE_DTTM, max(CR.LOG_DTTM) CLOSED_DTTM
          from CI_CASE     C1
    inner join CI_CASE_LOG CL on CL.CASE_ID = C1.CASE_ID   and CL.CASE_LOG_TYPE_FLG = 'CASC'
     left join CI_CASE_LOG CR on C1.CASE_COND_FLG = 'CLSD' and CR.CASE_ID = C1.CASE_ID  and CR.CASE_LOG_TYPE_FLG = 'STAT'
    group by C1.CASE_ID) C2 on C2.CASE_ID = CA.CASE_ID
order by CA.CASE_ID
