-- SELECT logic for CISADM.CI_TD_ENTRY_OPEN_VW
SELECT A."TD_ENTRY_ID",A."BATCH_CD",A."BATCH_NBR",A."MESSAGE_CAT_NBR",A."MESSAGE_NBR",A."ASSIGNED_TO",A."TD_TYPE_CD",A."ROLE_ID",A."ENTRY_STATUS_FLG",A."VERSION",A."CRE_DTTM",A."ASSIGNED_DTTM",A."COMPLETE_DTTM",A."COMPLETE_USER_ID",A."COMMENTS",A."ASSIGNED_USER_ID",A."TD_PRIORITY_FLG",A."ILM_DT",A."ILM_ARCH_SW",
(SELECT LISTAGG(msg_parm_val, '#') WITHIN GROUP (ORDER BY seq_num) FROM (select * from ci_td_msg_parm z where z.td_entry_id = a.td_entry_id))||'#' as PARMS_TLBL,
nvl((select key_value from ci_td_drlkey z where z.td_entry_id = a.td_entry_id and z.seq_num = ttyvw.dksq1),' ') as DKey1,
nvl((select key_value from ci_td_drlkey z where z.td_entry_id = a.td_entry_id and z.seq_num = ttyvw.dksq2),' ') as DKey2,
nvl((select key_value from ci_td_drlkey z where z.td_entry_id = a.td_entry_id and z.seq_num = ttyvw.dksq3),' ') as DKey3,
nvl((select key_value from ci_td_drlkey z where z.td_entry_id = a.td_entry_id and z.seq_num = ttyvw.dksq4),' ') as DKey4,
nvl((select key_value from ci_td_drlkey z where z.td_entry_id = a.td_entry_id and z.seq_num = ttyvw.dksq5),' ') as DKey5,
nvl((select key_value from ci_td_srtkey z where z.td_entry_id = a.td_entry_id and z.seq_num = ttyvw.sksq1),' ') as SKey1,
nvl((select key_value from ci_td_srtkey z where z.td_entry_id = a.td_entry_id and z.seq_num = ttyvw.sksq2),' ') as SKey2,
nvl((select key_value from ci_td_srtkey z where z.td_entry_id = a.td_entry_id and z.seq_num = ttyvw.sksq3),' ') as SKey3,
nvl((select key_value from ci_td_srtkey z where z.td_entry_id = a.td_entry_id and z.seq_num = ttyvw.sksq4),' ') as SKey4,
nvl((select key_value from ci_td_srtkey z where z.td_entry_id = a.td_entry_id and z.seq_num = ttyvw.sksq5),' ') as SKey5,
round((current_date - A.cre_dttm),0) as DAYS_OLD,
decode(a.comments,' ', nvl((select 'F1CMNT' from dual where exists (select 'x' from ci_td_log z where z.td_entry_id = a.td_entry_id and z.log_type_flg IN ('UDET','FWDD','SBCK'))),' '),'F1CMNT') COMMENTS_LOGS,
(
select decode(count(distinct TDC2.TD_ENTRY_ID),0,' ', count(distinct TDC2.TD_ENTRY_ID))
FROM
(select z.TD_ENTRY_ID, z.CHAR_TYPE_CD, z.SRCH_CHAR_VAL
from CI_TD_ENTRY_CHA z,
(select CT.CHAR_TYPE_CD
from CI_CHAR_TYPE CT,CI_FK_REF FKR,CI_MD_TBL TBL
where CT.CHAR_TYPE_FLG = 'FKV' AND
CT.FK_REF_CD = FKR.FK_REF_CD AND
FKR.TBL_NAME = TBL.TBL_NAME AND
TBL.TBL_CLASSIFICATION_FLG in ( 'F1MT','F1TT')
) fkrefs
where z.TD_ENTRY_ID = A.TD_ENTRY_ID
AND z.CHAR_TYPE_CD = fkrefs.CHAR_TYPE_CD
) TDC1,
CI_TD_ENTRY_CHA TDC2
WHERE TDC1.SRCH_CHAR_VAL = TDC2.SRCH_CHAR_VAL
AND TDC1.CHAR_TYPE_CD = TDC2.CHAR_TYPE_CD
AND TDC2.TD_ENTRY_ID <> A.TD_ENTRY_ID
and exists (select /*+ no_unnest */ 'x' from ci_td_entry q where TDC2.TD_ENTRY_ID = q.TD_ENTRY_ID and q.ENTRY_STATUS_FLG in ( 'O','W'))
) as RELATED_TODO_CNT,
ttyvw.dksq1, ttyvw.dksq2, ttyvw.dksq3, ttyvw.dksq4, ttyvw.dksq5,
ttyvw.sksq1, ttyvw.sksq2, ttyvw.sksq3, ttyvw.sksq4, ttyvw.sksq5
FROM CI_TD_ENTRY A,
(
select tdtyp.td_type_cd,
(select dkty.seq_num from (select td_type_cd, seq_num, ROW_NUMBER() OVER (PARTITION BY TD_TYPE_CD ORDER BY SEQ_NUM ASC) as seqno from CI_TD_DRLKEY_TY) dkty where dkty.td_type_cd = tdtyp.td_type_cd and dkty.seqno = 1) dksq1,
(select dkty.seq_num from (select td_type_cd, seq_num, ROW_NUMBER() OVER (PARTITION BY TD_TYPE_CD ORDER BY SEQ_NUM ASC) as seqno from CI_TD_DRLKEY_TY) dkty where dkty.td_type_cd = tdtyp.td_type_cd and dkty.seqno = 2) dksq2,
(select dkty.seq_num from (select td_type_cd, seq_num, ROW_NUMBER() OVER (PARTITION BY TD_TYPE_CD ORDER BY SEQ_NUM ASC) as seqno from CI_TD_DRLKEY_TY) dkty where dkty.td_type_cd = tdtyp.td_type_cd and dkty.seqno = 3) dksq3,
(select dkty.seq_num from (select td_type_cd, seq_num, ROW_NUMBER() OVER (PARTITION BY TD_TYPE_CD ORDER BY SEQ_NUM ASC) as seqno from CI_TD_DRLKEY_TY) dkty where dkty.td_type_cd = tdtyp.td_type_cd and dkty.seqno = 4) dksq4,
(select dkty.seq_num from (select td_type_cd, seq_num, ROW_NUMBER() OVER (PARTITION BY TD_TYPE_CD ORDER BY SEQ_NUM ASC) as seqno from CI_TD_DRLKEY_TY) dkty where dkty.td_type_cd = tdtyp.td_type_cd and dkty.seqno = 5) dksq5,
(select skty.seq_num from (select td_type_cd, seq_num, ROW_NUMBER() OVER (PARTITION BY TD_TYPE_CD ORDER BY SEQ_NUM ASC) as seqno from CI_TD_SRTKEY_TY) skty where skty.td_type_cd = tdtyp.td_type_cd and skty.seqno = 1) sksq1,
(select skty.seq_num from (select td_type_cd, seq_num, ROW_NUMBER() OVER (PARTITION BY TD_TYPE_CD ORDER BY SEQ_NUM ASC) as seqno from CI_TD_SRTKEY_TY) skty where skty.td_type_cd = tdtyp.td_type_cd and skty.seqno = 2) sksq2,
(select skty.seq_num from (select td_type_cd, seq_num, ROW_NUMBER() OVER (PARTITION BY TD_TYPE_CD ORDER BY SEQ_NUM ASC) as seqno from CI_TD_SRTKEY_TY) skty where skty.td_type_cd = tdtyp.td_type_cd and skty.seqno = 3) sksq3,
(select skty.seq_num from (select td_type_cd, seq_num, ROW_NUMBER() OVER (PARTITION BY TD_TYPE_CD ORDER BY SEQ_NUM ASC) as seqno from CI_TD_SRTKEY_TY) skty where skty.td_type_cd = tdtyp.td_type_cd and skty.seqno = 4) sksq4,
(select skty.seq_num from (select td_type_cd, seq_num, ROW_NUMBER() OVER (PARTITION BY TD_TYPE_CD ORDER BY SEQ_NUM ASC) as seqno from CI_TD_SRTKEY_TY) skty where skty.td_type_cd = tdtyp.td_type_cd and skty.seqno = 5) sksq5
from ci_td_type tdtyp
) ttyvw
WHERE A.ENTRY_STATUS_FLG in ( 'O','W')
and a.td_type_cd = ttyvw.td_type_cd
