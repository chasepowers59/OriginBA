-- SELECT logic for CISADM.CMS_C1_REPRESENTATIVE_BODA_VW
SELECT
          REP.C1_REPRESENTATIVE_CD
        , CAST(SVC_AREA.CM_ML_SVC_AREA AS VARCHAR2(30))                 AS CM_ML_SVC_AREA
        , CAST(WORK_CAPABILITY.CM_ML_WORKER_CAPABILITY AS VARCHAR2(16)) AS CM_ML_WORKER_CAPABILITY
FROM
          CISADM.C1_REPRESENTATIVE REP
          LEFT JOIN
                    XMLTABLE( '/root/cmMobileLiteDetails/serviceAreas/serviceAreaList' PASSING XMLTYPE(CONCAT(CONCAT('<root>', REP.BO_DATA_AREA), '</root>')) COLUMNS CM_ML_SVC_AREA VARCHAR2(50) PATH 'serviceArea' ) SVC_AREA
                    ON
                              1=1
          LEFT JOIN
                    XMLTABLE( '/root/cmMobileLiteDetails/workerCapability/capabilities' PASSING XMLTYPE(CONCAT(CONCAT('<root>', REP.BO_DATA_AREA), '</root>')) COLUMNS CM_ML_WORKER_CAPABILITY VARCHAR2(50) PATH 'capability' ) WORK_CAPABILITY
                    ON
                              1=1
