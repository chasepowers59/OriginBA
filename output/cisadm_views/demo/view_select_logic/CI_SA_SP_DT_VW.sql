-- SELECT logic for CISADM.CI_SA_SP_DT_VW
SELECT
              SP_ID,
              SA_SP_ID,
              SA_ID,
              START_DTTM,
              TO_CHAR(START_DTTM,'YYYY-MM-DD'),
              TO_CHAR(START_DTTM,'HH24.MI.SS."000000"'),
              START_MR_ID,
              STOP_DTTM,
              TO_CHAR(STOP_DTTM,'YYYY-MM-DD'),
              TO_CHAR(STOP_DTTM,'HH24.MI.SS."000000"'),
              USAGE_FLG,
              STOP_MR_ID,
              USE_PCT,
              VERSION
         FROM
              CI_SA_SP
 
