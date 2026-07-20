CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."CMS_D1_SP_BODA_VW" ("D1_SP_ID", "PERIODIC_EST_ELIGIBILITY_FLG", "OK_TO_ETR_LBL", "SP_WARN_LBL", "SP_INSTR_LBL", "SP_INSTR_DTS_LBL", "KEY_LBL", "D1_KEY_ID_LBL", "DEVICE_LOC_LBL", "DEVICE_LOC_DTS_LBL") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  SELECT
          SP.D1_SP_ID
        , CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', SP.BO_DATA_AREA), '</root>')), 'root/periodicEstimationEligibility') AS VARCHAR2(4)) AS PERIODIC_EST_ELIGIBILITY_FLG
        , CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', SP.BO_DATA_AREA), '</root>')), 'root/okToEnter') AS VARCHAR2(30))                    AS OK_TO_ETR_LBL
        , CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', SP.BO_DATA_AREA), '</root>')), 'root/spWarning') AS VARCHAR2(30))                    AS SP_WARN_LBL
        , CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', SP.BO_DATA_AREA), '</root>')), 'root/spInstruction') AS VARCHAR2(30))                AS SP_INSTR_LBL
        , CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', SP.BO_DATA_AREA), '</root>')), 'root/spInstructionDetails') AS VARCHAR2(250))        AS SP_INSTR_DTS_LBL
        , CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', SP.BO_DATA_AREA), '</root>')), 'root/key') AS VARCHAR2(30))                          AS KEY_LBL
        , CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', SP.BO_DATA_AREA), '</root>')), 'root/keyId') AS VARCHAR2(30))                        AS D1_KEY_ID_LBL
        , CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', SP.BO_DATA_AREA), '</root>')), 'root/deviceLocation') AS VARCHAR2(30))               AS DEVICE_LOC_LBL
        , CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', SP.BO_DATA_AREA), '</root>')), 'root/deviceLocationDetails') AS VARCHAR2(250))       AS DEVICE_LOC_DTS_LBL
FROM
          CISADM.D1_SP SP;
