-- SELECT logic for CISADM.CMS_CI_APPR_REQ_BODA_VW
SELECT
       APREQ.APPR_REQ_ID
    , CAST(COALESCE(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', APREQ.BO_DATA_AREA), '</root>')),'root/adjustmentId'), RPAD(' ', 12)) AS CHAR(12))                       AS ADJ_ID
    , TO_DATE(NULLIF(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', APREQ.BO_DATA_AREA), '</root>')),'root/approvalInfo/accountingDate'), ''), 'YYYY-MM-DD')             AS ACCOUNTING_DT
    , CAST(COALESCE(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', APREQ.BO_DATA_AREA), '</root>')),'root/approvalInfo/currentApprovalToDoId'), RPAD(' ', 14)) AS CHAR(14)) AS TD_ENTRY_ID
    , CAST(COALESCE(EXTRACTVALUE(XMLTYPE(CONCAT(CONCAT('<root>', APREQ.BO_DATA_AREA), '</root>')),'root/rejectInfo/rejectReason'), RPAD(' ', 4)) AS CHAR(4))             AS C1_AREQ_REJECT_RSN_FLG
FROM
       CISADM.CI_APPR_REQ APREQ
