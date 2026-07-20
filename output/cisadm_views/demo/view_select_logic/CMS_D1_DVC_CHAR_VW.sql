-- SELECT logic for CISADM.CMS_D1_DVC_CHAR_VW
SELECT
         D1_DEVICE_ID
       , CAST(MIN(MXU_TYPE) AS CHAR(16))     AS MXU_TYPE
FROM
         (
                SELECT
                       D1_DEVICE_ID
                     , DECODE(trim(CHAR_TYPE_CD), 'CMCMXUTY', TRIM(SRCH_CHAR_VAL), NULL) AS MXU_TYPE
                FROM
                       CISADM.D1_DVC_CHAR
         )
WHERE
         MXU_TYPE IS NOT NULL
GROUP BY
         D1_DEVICE_ID
