-- SELECT logic for CISADM.D1_EXT_US_SCLR_MDS_MSRMTS_VW
select C.US_ID
	  ,CASE
          WHEN C.EXT_TO_SI = 'D1YS' AND C.SOURCE_ID_TYPE_CD <> 'D1US'
              THEN (SELECT max(TRGT.US_ID)
                    FROM   D1_US_IDENTIFIER SRC
                    INNER JOIN D1_US_IDENTIFIER TRGT
                      ON TRGT.ID_VALUE = SRC.ID_VALUE
                      AND TRGT.US_ID_TYPE_FLG = C.TARGET_ID_TYPE_CD
                      AND TRGT.US_ID <> SRC.US_ID
                    WHERE SRC.US_ID_TYPE_FLG = C.SOURCE_ID_TYPE_CD
                    AND   SRC.US_ID = C.US_ID
                    having count(*) = 1)
          WHEN C.EXT_TO_SI = 'D1YS' AND C.SOURCE_ID_TYPE_CD = 'D1US'
              THEN (SELECT max(TRGT.US_ID)
                    FROM  D1_US_IDENTIFIER TRGT
                   WHERE  TRGT.ID_VALUE = C.US_ID
                      AND TRGT.US_ID_TYPE_FLG = C.TARGET_ID_TYPE_CD
                      AND TRGT.US_ID <> C.US_ID
                   having count(*) = 1)
          ELSE null
     end SI_US
    ,C.MEASR_COMP_ID MC_ID
	,C.EXT_TO_SI E_SI
    ,C.SOURCE_ID_TYPE_CD SI_CD
    ,C.TARGET_ID_TYPE_CD TI_CD
    ,nvl(m.prev_msrmt_dttm,m.msrmt_dttm) P_DTTM
    ,m.msrmt_dttm M_DTTM
    ,m.MSRMT_USE_FLG MUSE_FLG
    ,m.MSRMT_COND_FLG MCOND_FLG
    , DECODE(C.VALUE_ID_TYPE_FLG,'1',m.MSRMT_VAL1,'2',m.MSRMT_VAL2,'3',m.MSRMT_VAL3,'4',m.MSRMT_VAL4
       ,'5',m.MSRMT_VAL5,'6',m.MSRMT_VAL6,'7',m.MSRMT_VAL7,'8',m.MSRMT_VAL8,'9',m.MSRMT_VAL9,'10'
       ,m.MSRMT_VAL10,m.MSRMT_VAL) * USAGE_MULT
       MSRMT_VAL
    from D1_EXT_US_SCLR_MDS_CONST_VW C
    INNER JOIN D1_MSRMT M on M.MEASR_COMP_ID = C.MEASR_COMP_ID
        AND M.MSRMT_DTTM > c.START_DTTM
        AND ( m.PREV_MSRMT_DTTM < c.END_DTTM or m.PREV_MSRMT_DTTM is null )
        AND m.MSRMT_DTTM in (
            SELECT MA.MSRMT_DTTM
            FROM D1_MSRMT MA
            WHERE MA.MEASR_COMP_ID = m.MEASR_COMP_ID
            AND MA.MSRMT_DTTM >= c.START_DTTM
            AND MA.MSRMT_DTTM <= c.END_DTTM
            AND MA.MSRMT_USE_FLG <> 'D101'
            UNION
            SELECT
            MIN(MB.MSRMT_DTTM)
            FROM D1_MSRMT MB
            WHERE MB.MEASR_COMP_ID = m.MEASR_COMP_ID
            AND MB.MSRMT_DTTM > c.END_DTTM
            AND MB.MSRMT_USE_FLG <> 'D101'
         )
