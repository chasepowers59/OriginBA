-- SELECT logic for CISADM.CI_CFG_SPMR2_VW
SELECT
              A.SP_MTR_HIST_ID,
              A.SP_ID,
              A.MTR_CONFIG_ID,
              A.INSTALL_CONST,
              B.MR_ID,
              A.REMOVAL_MR_ID,
              TO_CHAR(C.READ_DTTM,'YYYY-MM-DD'),
              TO_CHAR(C.READ_DTTM,'HH24.MI.SS."000000"'),
              TO_CHAR(A.REMOVAL_DTTM,'YYYY-MM-DD'),
              TO_CHAR(A.REMOVAL_DTTM,'HH24.MI.SS."000000"')
         FROM
              CI_SP_MTR_HIST A,
              CI_SP_MTR_EVT B,
              CI_MR C
        WHERE
              A.SP_MTR_HIST_ID =  B.SP_MTR_HIST_ID
          AND B.SP_MTR_EVT_FLG =  'I'
          AND B.MR_ID =  C.MR_ID
 
