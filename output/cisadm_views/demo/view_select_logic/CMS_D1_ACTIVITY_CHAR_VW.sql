-- SELECT logic for CISADM.CMS_D1_ACTIVITY_CHAR_VW
SELECT   D1_ACTIVITY_ID,
         MIN(FA_INT_STATUS_FLG) AS FA_INT_STATUS_FLG,
         MIN(FA_PRIORITY_FLG) AS FA_PRIORITY_FLG,
         MIN(THRD_PTY_REP_CD) AS THRD_PTY_REP_CD
FROM    ( SELECT  AC.D1_ACTIVITY_ID,
                  DECODE(trim(AC.CHAR_TYPE_CD),
                                  'CMFAINST', ac.srch_char_val,
                                  NULL) AS FA_INT_STATUS_FLG,
                  DECODE(trim(AC.CHAR_TYPE_CD),
                                  'CMFAPRIO', ac.srch_char_val,
                                  NULL) AS FA_PRIORITY_FLG,
                  DECODE(trim(AC.CHAR_TYPE_CD),
                                  'CMFAREP', ac.srch_char_val,
                                  NULL) || '  ' AS THRD_PTY_REP_CD
         FROM     CISADM.D1_ACTIVITY_CHAR AC )
GROUP BY D1_ACTIVITY_ID
