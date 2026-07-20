-- SELECT logic for CISADM.CMS_D1_DVC_IDENTIFIER_VW
SELECT
         D1_DEVICE_ID
       , CAST(MIN(ASSET_ID) AS VARCHAR2(60))                                                                                               AS ASSET_ID
       , CAST(MIN(BADGE_NUMBER) AS VARCHAR2(60))                                                                                           AS BADGE_NUMBER
       , CAST(MIN(CONFIGURATION) AS VARCHAR2(60))                                                                                          AS CONFIGURATION
       , CAST(MIN(EXTERNAL_ID) AS VARCHAR2(60))                                                                                            AS EXTERNAL_ID
       , CAST(MIN(INTERNAL_METER_NUMBER) AS VARCHAR2(60))                                                                                  AS INTERNAL_METER_NUMBER
       , CAST(MIN(MDM_EXTERNAL_ID) AS VARCHAR2(14))                                                                                        AS MDM_EXTERNAL_ID
       , CAST(MIN(NIC_ID) AS VARCHAR2(120))                                                                                                AS NIC_ID
       , CAST(MIN(PALLET_NUMBER) AS VARCHAR2(14))                                                                                          AS PALLET_NUMBER
       , CAST(MIN(SERIAL_NUMBER) AS VARCHAR2(60))                                                                                          AS SERIAL_NUMBER
       , CAST(MIN(SPECIFICATION) AS VARCHAR2(60))                                                                                          AS SPECIFICATION
       , CAST(MIN(NEURON_ID) AS VARCHAR2(60))                                                                                              AS NEURON_ID
       , CAST(MIN(NAME) AS VARCHAR2(60))                                                                                                   AS NAME
       , CAST(MIN(NIC_SERIAL_NUMBER) AS VARCHAR2(60))                                                                                      AS NIC_SERIAL_NUMBER
       , CAST(MIN(UTILITY_DEVICE_ID) AS VARCHAR2(60))                                                                                      AS UTILITY_DEVICE_ID
FROM
         (
                SELECT
                       D1_DEVICE_ID
                     , DECODE(trim(DVC_ID_TYPE_FLG), 'D1AS', TRIM(ID_VALUE), NULL) AS ASSET_ID
                     , DECODE(trim(DVC_ID_TYPE_FLG), 'D1BN', TRIM(ID_VALUE), NULL) AS BADGE_NUMBER
                     , DECODE(trim(DVC_ID_TYPE_FLG), 'D1CO', TRIM(ID_VALUE), NULL) AS CONFIGURATION
                     , DECODE(trim(DVC_ID_TYPE_FLG), 'D1EI', TRIM(ID_VALUE), NULL) AS EXTERNAL_ID
                     , DECODE(trim(DVC_ID_TYPE_FLG), 'D1IN', TRIM(ID_VALUE), NULL) AS INTERNAL_METER_NUMBER
                     , DECODE(trim(DVC_ID_TYPE_FLG), 'D1MI', TRIM(ID_VALUE), NULL) AS MDM_EXTERNAL_ID
                     , DECODE(trim(DVC_ID_TYPE_FLG), 'D1NI', TRIM(ID_VALUE), NULL) AS NIC_ID
                     , DECODE(trim(DVC_ID_TYPE_FLG), 'D1PN', TRIM(ID_VALUE), NULL) AS PALLET_NUMBER
                     , DECODE(trim(DVC_ID_TYPE_FLG), 'D1SN', TRIM(ID_VALUE), NULL) AS SERIAL_NUMBER
                     , DECODE(trim(DVC_ID_TYPE_FLG), 'D1SP', TRIM(ID_VALUE), NULL) AS SPECIFICATION
                     , DECODE(trim(DVC_ID_TYPE_FLG), 'D4NR', TRIM(ID_VALUE), NULL) AS NEURON_ID
                     , DECODE(trim(DVC_ID_TYPE_FLG), 'D7NA', TRIM(ID_VALUE), NULL) AS NAME
                     , DECODE(trim(DVC_ID_TYPE_FLG), 'D7NS', TRIM(ID_VALUE), NULL) AS NIC_SERIAL_NUMBER
                     , DECODE(trim(DVC_ID_TYPE_FLG), 'D7UD', TRIM(ID_VALUE), NULL) AS UTILITY_DEVICE_ID
                FROM
                       CISADM.D1_DVC_IDENTIFIER
         )
GROUP BY
         D1_DEVICE_ID
