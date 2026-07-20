-- SELECT logic for CISADM.D2_QUALITY_CNT_MV
SELECT T1.MEASR_COMP_ID AS  MEASR_COMP_ID,
    T1.measr_comp_type_Cd as MEASR_COMP_TYPE_CD,
    T1.POSTAL AS POSTAL ,
    MCTYP.DESCR100 AS MC_TYPE_DESCR ,
    T1.CITY  AS CITY,
    T1.DEVICE_TYPE_CD AS  DEVICE_TYPE_CD,
    DVTL.DESCR100 AS DEVICE_TYPE_DESCR ,
    T1.HEAD_END_SYSTEM_CD AS HEAD_END_SYSTEM_CD ,
    SPRL.DESCR100 AS HEAD_END_SYSTEM_DESCR ,
    T1.USG_CALC_GRP_CD AS USG_CALC_GRP_CD,
    USGRL.DESCR100 AS USG_CALC_GRP_DESCR ,
    T1.MKT_CD AS MKT_CD,
    MKTL.DESCR100 AS MKT_DESCR ,
    T1.SPR_CD AS D1_SPR_CD ,
    SPRL1.DESCR100 AS SPR_DESCR ,
    T1.D1_SVC_TPE_CD  AS D1_SVC_TPE_CD,
    SVTL.DESCR100 AS SVC_TYPE_DESCR ,
    T1.MKT_REL_TYPE_FLG AS MKT_REL_TYPE_FLG ,
    LKPL.DESCR AS MKT_REL_TYPE_DESCR ,
    T1.MANUFACTURER_CD AS MANUFACTURER_CD,
    DMNL.DESCR100 AS MANUFACTURER_DESCR ,
    T1.D1_MODEL_CD AS D1_MODEL_CD,
    DMDL.DESCR100 AS MODEL_DESCR ,
    T1.GEO_CODE AS GEO_CODE
  FROM
    (SELECT
      /*+ INDEX(mc,D1M252S2) */
      mc.measr_comp_id,
      mastermc.measr_comp_type_Cd,
      MAX(DECODE(m.char_type_cd ,'D2POSTCD',m.SRCH_CHAR_VAL,NULL))       AS postal,
      MAX(DECODE(trim(m.char_type_cd) ,'D2CITY',m.SRCH_CHAR_VAL,NULL))   AS city,
      MAX(DECODE(trim(m.char_type_cd) ,'D2DVCTYP',m.SRCH_CHAR_VAL,NULL)) AS DEVICE_TYPE_CD,
      MAX(DECODE(trim(m.char_type_cd) ,'D2HEADED',m.SRCH_CHAR_VAL,NULL)) AS head_end_system_cd,
      MAX(DECODE(trim(m.char_type_cd) ,'D2USGGRP',m.SRCH_CHAR_VAL,NULL)) AS usg_calc_grp_cd,
      MAX(DECODE(trim(m.char_type_cd) ,'D2MARKET',m.SRCH_CHAR_VAL,NULL)) AS mkt_cd,
      MAX(DECODE(trim(m.char_type_cd) ,'D2SPR',m.SRCH_CHAR_VAL,NULL))    AS spr_cd,
      MAX(DECODE(trim(m.char_type_cd) ,'D2SVCTYP',m.SRCH_CHAR_VAL,NULL)) AS d1_svc_tpe_cd,
      MAX(DECODE(trim(m.char_type_cd) ,'D2MKRLTY',m.SRCH_CHAR_VAL,NULL)) AS mkt_rel_type_flg,
      MAX(DECODE(trim(m.char_type_cd) ,'D2MANUF',m.SRCH_CHAR_VAL,NULL))  AS manufacturer_cd,
      MAX(DECODE(trim(m.char_type_cd) ,'D2MODEL',m.SRCH_CHAR_VAL,NULL))  AS d1_model_cd,
      MAX(DECODE(trim(m.char_type_cd) ,'D2GEOCD',m.SRCH_CHAR_VAL,NULL))  AS geo_code,
      mc.bus_obj_cd,
      f1.language_cd
    FROM d1_measr_comp mc,
      d1_measr_comp_type mct,
      d1_measr_comp_char m,
      d1_measr_comp_rel mcrel,
      d1_measr_comp mastermc,
      f1_installation f1
    WHERE mc.measr_comp_id    =m.measr_comp_id
    AND m.char_type_cd       IN ('D2POSTCD' ,'D2CITY','D2DVCTYP','D2HEADED','D2USGGRP','D2MARKET','D2SPR','D2SVCTYP','D2MKRLTY','D2MANUF','D2MODEL','D2GEOCD')
    AND mc.bus_obj_cd         = 'D2-MsrmtQualityCountAggregator'
    AND mc.BO_STATUS_CD       = 'ACTIVE'
    AND mastermc.measr_comp_type_cd = mct.measr_comp_type_cd
    AND mct.mc_class_flg      = 'D1AG'
    AND mcrel.rel_measr_comp_id =mc.measr_comp_id
    AND mastermc.measr_comp_id = mcrel.measr_comp_id
    AND m.effdt               =
      (SELECT MAX (a.effdt)
      FROM d1_measr_comp_char a
      WHERE a.measr_comp_id = m.measr_comp_id
      AND a.char_type_cd    = m.char_type_cd
      )
    GROUP BY mc.measr_comp_id,
      mastermc.measr_comp_type_Cd,
      mc.bus_obj_cd,
      f1.language_cd
    ) T1,
    d1_measr_comp_type_l mctyp,
    d1_dvc_type_l dvtl,
    d1_spr_l sprl,
    d1_usg_grp_l usgrl,
    d1_mkt_l mktl,
    d1_spr_l sprl1,
    d1_svc_type_l svtl,
    ci_lookup_val_l lkpl,
    d1_manufacturer_l dmnl,
    d1_model_l dmdl
  WHERE T1.measr_comp_type_cd=mctyp.measr_comp_type_cd
  AND mctyp.language_cd      = T1.language_cd
  AND T1.DEVICE_TYPE_CD      =dvtl.device_type_cd
  AND T1.language_cd         = dvtl.language_cd
  AND T1.head_end_system_cd  =sprl.d1_spr_cd(+)
  AND T1.language_cd         = sprl.language_cd(+)
  AND T1.usg_calc_grp_cd     =usgrl.usg_grp_cd(+)
  AND T1.language_cd         = usgrl.language_cd(+)
  AND T1.mkt_cd              =mktl.mkt_cd(+)
  AND T1.language_cd         = mktl.language_cd(+)
  AND T1.spr_cd              =sprl1.d1_spr_cd(+)
  AND T1.language_cd         = sprl1.language_cd(+)
  AND T1.d1_svc_tpe_cd       =svtl.d1_svc_type_cd(+)
  AND T1.language_cd         = svtl.language_cd(+)
  AND T1.mkt_rel_type_flg    =lkpl.field_value(+)
  AND T1.language_cd         = lkpl.language_cd(+)
  AND lkpl.field_name(+)     = 'MKT_REL_TYPE_FLG'
  AND T1.manufacturer_cd     =dmnl.manufacturer_cd(+)
  AND T1.manufacturer_cd    = dmdl.manufacturer_cd(+)
  AND T1.language_cd         = dmnl.language_cd(+)
  AND T1.d1_model_cd         =dmdl.d1_model_cd(+)
  AND T1.language_cd         = dmdl.language_cd(+)
