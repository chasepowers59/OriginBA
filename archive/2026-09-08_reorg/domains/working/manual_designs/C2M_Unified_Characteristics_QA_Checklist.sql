-- C2M Unified Characteristics Domain QA Checklist
-- Purpose: validate raw characteristic-row parity, decode coverage, and object-level distinct parity.
-- Scope: PERSON (CI_PER_CHAR), ACCOUNT (CI_ACCT_CHAR), SA (CI_SA_CHAR), PREMISE (CI_PREM_CHAR), SP (D1_SP_CHAR)

--------------------------------------------------------------------------------
-- 1) Source row counts by object type (baseline)
--------------------------------------------------------------------------------
select 'PERSON' as object_type, count(*) as src_row_count from cisadm.ci_per_char
union all
select 'ACCOUNT' as object_type, count(*) as src_row_count from cisadm.ci_acct_char
union all
select 'SA' as object_type, count(*) as src_row_count from cisadm.ci_sa_char
union all
select 'PREMISE' as object_type, count(*) as src_row_count from cisadm.ci_prem_char
union all
select 'SP' as object_type, count(*) as src_row_count from cisadm.d1_sp_char;

--------------------------------------------------------------------------------
-- 2) Distinct object counts in source characteristic tables
--------------------------------------------------------------------------------
select 'PERSON' as object_type, count(distinct per_id) as distinct_object_count from cisadm.ci_per_char
union all
select 'ACCOUNT' as object_type, count(distinct acct_id) as distinct_object_count from cisadm.ci_acct_char
union all
select 'SA' as object_type, count(distinct sa_id) as distinct_object_count from cisadm.ci_sa_char
union all
select 'PREMISE' as object_type, count(distinct prem_id) as distinct_object_count from cisadm.ci_prem_char
union all
select 'SP' as object_type, count(distinct d1_sp_id) as distinct_object_count from cisadm.d1_sp_char;

--------------------------------------------------------------------------------
-- 3) Character type decode coverage (LANGUAGE_CD='ENG')
--------------------------------------------------------------------------------
with unified_char as (
    select 'PERSON' as object_type, per_id as object_id, char_type_cd from cisadm.ci_per_char
    union all
    select 'ACCOUNT' as object_type, acct_id as object_id, char_type_cd from cisadm.ci_acct_char
    union all
    select 'SA' as object_type, sa_id as object_id, char_type_cd from cisadm.ci_sa_char
    union all
    select 'PREMISE' as object_type, prem_id as object_id, char_type_cd from cisadm.ci_prem_char
    union all
    select 'SP' as object_type, d1_sp_id as object_id, char_type_cd from cisadm.d1_sp_char
)
select
    u.object_type,
    count(*) as char_rows,
    sum(case when l.char_type_cd is null then 1 else 0 end) as missing_char_type_descr_rows,
    round(100 * sum(case when l.char_type_cd is null then 1 else 0 end) / nullif(count(*),0), 2) as missing_descr_pct
from unified_char u
left join cisadm.ci_char_type_l l
    on l.char_type_cd = u.char_type_cd
   and l.language_cd = 'ENG'
group by u.object_type
order by u.object_type;

--------------------------------------------------------------------------------
-- 4) Top missing char types (if decode gaps exist)
--------------------------------------------------------------------------------
with unified_char as (
    select 'PERSON' as object_type, char_type_cd from cisadm.ci_per_char
    union all
    select 'ACCOUNT' as object_type, char_type_cd from cisadm.ci_acct_char
    union all
    select 'SA' as object_type, char_type_cd from cisadm.ci_sa_char
    union all
    select 'PREMISE' as object_type, char_type_cd from cisadm.ci_prem_char
    union all
    select 'SP' as object_type, char_type_cd from cisadm.d1_sp_char
)
select
    u.object_type,
    u.char_type_cd,
    count(*) as missing_rows
from unified_char u
left join cisadm.ci_char_type_l l
    on l.char_type_cd = u.char_type_cd
   and l.language_cd = 'ENG'
where l.char_type_cd is null
group by u.object_type, u.char_type_cd
order by missing_rows desc, u.object_type, u.char_type_cd;

--------------------------------------------------------------------------------
-- 5) Grain sanity checks (duplicate row-key detection in source)
--    Row-key definition from domain design:
--    object_id || '|' || char_type_cd || '|' || effdt
--------------------------------------------------------------------------------
with unified_char as (
    select 'PERSON' as object_type, per_id as object_id, char_type_cd, effdt from cisadm.ci_per_char
    union all
    select 'ACCOUNT' as object_type, acct_id as object_id, char_type_cd, effdt from cisadm.ci_acct_char
    union all
    select 'SA' as object_type, sa_id as object_id, char_type_cd, effdt from cisadm.ci_sa_char
    union all
    select 'PREMISE' as object_type, prem_id as object_id, char_type_cd, effdt from cisadm.ci_prem_char
    union all
    select 'SP' as object_type, d1_sp_id as object_id, char_type_cd, effdt from cisadm.d1_sp_char
)
select
    object_type,
    object_id,
    char_type_cd,
    effdt,
    count(*) as dup_count
from unified_char
group by object_type, object_id, char_type_cd, effdt
having count(*) > 1
order by dup_count desc, object_type, object_id;

--------------------------------------------------------------------------------
-- 6) Spot check: sample decoded characteristic types per object
--------------------------------------------------------------------------------
with unified_char as (
    select 'PERSON' as object_type, per_id as object_id, char_type_cd, char_val from cisadm.ci_per_char
    union all
    select 'ACCOUNT' as object_type, acct_id as object_id, char_type_cd, char_val from cisadm.ci_acct_char
    union all
    select 'SA' as object_type, sa_id as object_id, char_type_cd, char_val from cisadm.ci_sa_char
    union all
    select 'PREMISE' as object_type, prem_id as object_id, char_type_cd, char_val from cisadm.ci_prem_char
    union all
    select 'SP' as object_type, d1_sp_id as object_id, char_type_cd, char_val from cisadm.d1_sp_char
)
select *
from (
    select
        u.object_type,
        u.object_id,
        u.char_type_cd,
        l.descr as char_type_descr,
        u.char_val,
        row_number() over (partition by u.object_type order by u.object_id, u.char_type_cd) as rn
    from unified_char u
    left join cisadm.ci_char_type_l l
        on l.char_type_cd = u.char_type_cd
       and l.language_cd = 'ENG'
) x
where x.rn <= 25
order by x.object_type, x.rn;
