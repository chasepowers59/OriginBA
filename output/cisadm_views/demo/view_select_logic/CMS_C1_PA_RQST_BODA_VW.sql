-- SELECT logic for CISADM.CMS_C1_PA_RQST_BODA_VW
SELECT
          PA.PA_RQST_ID
        , RELOBJ.PK_VALUE1                                                                                                                           AS SA_ID
        , TO_NUMBER(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', PA.BO_XML_DATA_AREA), '</root>')), 'root/BO_XML_DATA_AREA/paymentAmount'))                          AS PA_RQST_DOWN_PAY_PAYMENT
        , TO_NUMBER(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', PA.BO_XML_DATA_AREA), '</root>')), 'root/BO_XML_DATA_AREA/recalculated/remainingAmount'))           AS PA_REMAINING_AMOUNT
        , TO_NUMBER(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', PA.BO_XML_DATA_AREA), '</root>')), 'root/BO_XML_DATA_AREA/recalculated/numberOfInstallments'))      AS PA_RQST_NBR_INSTALLMENT
        , TO_NUMBER(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', PA.BO_XML_DATA_AREA), '</root>')), 'root/BO_XML_DATA_AREA/recalculated/installmentAmount'))         AS PA_RQST_INSTALLMENT_AMT
        , CAST(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', PA.BO_XML_DATA_AREA), '</root>')), 'root/BO_XML_DATA_AREA/recalculated/termsSummary') AS VARCHAR2(4000)) AS PA_PAYMENT_TERMS
        , TO_NUMBER(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', RELOBJ.BO_XML_DATA_AREA), '</root>')), 'root/BO_XML_DATA_AREA/currentBalance'))                     AS PA_RQST_CUR_BAL
        , TO_NUMBER(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', RELOBJ.BO_XML_DATA_AREA), '</root>')), 'root/BO_XML_DATA_AREA/amount'))                             AS PA_RQST_SA_AMT
        , TO_NUMBER(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', RELOBJ.BO_XML_DATA_AREA), '</root>')), 'root/BO_XML_DATA_AREA/recalculated/amount'))                AS PA_RQST_SA_AMT_RECALC
FROM
          CISADM.C1_PA_RQST PA
        , CISADM.C1_PA_RQST_REL_OBJ RELOBJ
WHERE
          PA.PA_RQST_ID                       = RELOBJ.PA_RQST_ID (+)
          AND RELOBJ.PA_RQST_REL_OBJ_TYPE_FLG(+) = 'C1SA'
          AND RELOBJ.MAINT_OBJ_CD(+)             = 'SA'
