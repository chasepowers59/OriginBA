-- Read-only benchmark script for 6 updated usage/billing domains (last 30 days)
-- Run in SQLcl/SQL*Plus with a read-only user.
-- Capture output including elapsed timings from "set timing on".

set echo on
set timing on
set pagesize 200
set linesize 220
set trimspool on
set verify off

prompt ===== CASE 1: usage_billing_fin_bridge_perffast =====
with usage_base as (
    select u.bill_id,
           u.bseg_id,
           u.sa_id,
           u.acct_id,
           u.rs_cd,
           u.uom_cd,
           u.tou_cd,
           u.sqi_cd,
           u.ft_type_flg,
           u.accounting_dt
      from cisadm.c1_bi_billed_usage_vw u
     where u.accounting_dt >= trunc(sysdate) - 30
       and u.accounting_dt < trunc(sysdate) + 1
       and u.bill_id is not null
       and u.bseg_id is not null
       and u.rs_cd is not null
),
usage_keys as (
    select distinct ub.bill_id, ub.bseg_id, ub.rs_cd
      from usage_base ub
),
ft_filtered as (
    select f.bill_id,
           f.bseg_id,
           f.rs_cd,
           nvl(f.ft_gl_rev_amt, 0) as ft_gl_rev_amt,
           nvl(f.ft_gl_tax_amt, 0) as ft_gl_tax_amt,
           nvl(f.ft_other_amt, 0) as ft_other_amt,
           nvl(f.tot_amt, 0) as tot_amt,
           nvl(f.ft_cnt, 0) as ft_cnt
      from cisadm.c1_bi_ft_vw f
      join usage_keys uk
        on uk.bill_id = f.bill_id
       and uk.bseg_id = f.bseg_id
       and uk.rs_cd = f.rs_cd
     where f.accounting_dt >= trunc(sysdate) - 30
       and f.accounting_dt < trunc(sysdate) + 1
       and f.bill_id is not null
       and f.bseg_id is not null
       and f.rs_cd is not null
),
ft_agg as (
    select ff.bill_id, ff.bseg_id, ff.rs_cd
      from ft_filtered ff
     group by ff.bill_id, ff.bseg_id, ff.rs_cd
)
select 'usage_billing_fin_bridge_perffast' as case_key,
       count(*) as row_count
  from usage_base ub
  left join ft_agg fa
    on fa.bill_id = ub.bill_id
   and fa.bseg_id = ub.bseg_id
   and fa.rs_cd = ub.rs_cd;
/

prompt ===== CASE 2: usage_billing_fin_bridge_ultrasafe =====
with usage_base as (
    select u.bill_id,
           u.bseg_id,
           u.sa_id,
           u.acct_id,
           u.rs_cd,
           u.uom_cd,
           u.tou_cd,
           u.sqi_cd,
           u.ft_type_flg,
           u.accounting_dt
      from cisadm.c1_bi_billed_usage_vw u
     where u.accounting_dt >= trunc(sysdate) - 30
       and u.accounting_dt < trunc(sysdate) + 1
       and u.bill_id is not null
       and u.bseg_id is not null
       and u.rs_cd is not null
),
usage_keys as (
    select distinct ub.bill_id, ub.bseg_id, ub.rs_cd
      from usage_base ub
)
select 'usage_billing_fin_bridge_ultrasafe' as case_key,
       count(*) as row_count
  from usage_base ub
  left join (
      select f.bill_id, f.bseg_id, f.rs_cd
        from cisadm.c1_bi_ft_vw f
        join usage_keys uk
          on uk.bill_id = f.bill_id
         and uk.bseg_id = f.bseg_id
         and uk.rs_cd = f.rs_cd
       where f.accounting_dt >= trunc(sysdate) - 30
         and f.accounting_dt < trunc(sysdate) + 1
         and f.bill_id is not null
         and f.bseg_id is not null
         and f.rs_cd is not null
  ) ft
    on ft.bill_id = ub.bill_id
   and ft.bseg_id = ub.bseg_id
   and ft.rs_cd = ub.rs_cd;
/

prompt ===== CASE 3: billed_revenue_rate_component =====
with usage_base as (
    select u.bill_id,
           u.bseg_id,
           u.sa_id,
           u.acct_id,
           u.rs_cd,
           u.uom_cd,
           u.tou_cd,
           u.sqi_cd,
           u.ft_type_flg,
           u.accounting_dt
      from cisadm.c1_bi_billed_usage_vw u
     where u.accounting_dt >= trunc(sysdate) - 30
       and u.accounting_dt < trunc(sysdate) + 1
       and u.bill_id is not null
       and u.bseg_id is not null
       and u.rs_cd is not null
),
usage_keys as (
    select distinct ub.bseg_id, ub.uom_cd, ub.tou_cd, ub.sqi_cd
      from usage_base ub
     where ub.uom_cd is not null
       and ub.tou_cd is not null
       and ub.sqi_cd is not null
),
rc_component_ctx as (
    select bcl.bseg_id,
           bcl.uom_cd,
           bcl.tou_cd,
           bcl.sqi_cd
      from cisadm.ci_bseg_calc_ln bcl
      join usage_keys uk
        on uk.bseg_id = bcl.bseg_id
       and uk.uom_cd = bcl.uom_cd
       and uk.tou_cd = bcl.tou_cd
       and uk.sqi_cd = bcl.sqi_cd
      join cisadm.ci_bseg_calc bc
        on bc.bseg_id = bcl.bseg_id
       and bc.header_seq = bcl.header_seq
      left join cisadm.ci_rc rc
        on rc.rs_cd = bc.rs_cd
       and rc.rc_seq = bcl.rc_seq
       and rc.effdt = bc.effdt
)
select 'billed_revenue_rate_component' as case_key,
       count(*) as row_count
  from usage_base ub
  join rc_component_ctx rcx
    on rcx.bseg_id = ub.bseg_id
   and rcx.uom_cd = ub.uom_cd
   and rcx.tou_cd = ub.tou_cd
   and rcx.sqi_cd = ub.sqi_cd;
/

prompt ===== CASE 4: billed_revenue_tax_lean =====
with usage_base as (
    select u.bill_id,
           u.bseg_id,
           u.sa_id,
           u.acct_id,
           u.rs_cd,
           u.uom_cd,
           u.tou_cd,
           u.sqi_cd,
           u.ft_type_flg,
           u.accounting_dt
      from cisadm.c1_bi_billed_usage_vw u
     where u.accounting_dt >= trunc(sysdate) - 30
       and u.accounting_dt < trunc(sysdate) + 1
       and u.bill_id is not null
       and u.bseg_id is not null
       and u.rs_cd is not null
),
usage_keys as (
    select distinct ub.bseg_id, ub.uom_cd, ub.tou_cd, ub.sqi_cd
      from usage_base ub
     where ub.uom_cd is not null
       and ub.tou_cd is not null
       and ub.sqi_cd is not null
),
rc_component_ctx as (
    select bcl.bseg_id,
           bcl.uom_cd,
           bcl.tou_cd,
           bcl.sqi_cd
      from cisadm.ci_bseg_calc_ln bcl
      join usage_keys uk
        on uk.bseg_id = bcl.bseg_id
       and uk.uom_cd = bcl.uom_cd
       and uk.tou_cd = bcl.tou_cd
       and uk.sqi_cd = bcl.sqi_cd
      join cisadm.ci_bseg_calc bc
        on bc.bseg_id = bcl.bseg_id
       and bc.header_seq = bcl.header_seq
      left join cisadm.ci_rc rc
        on rc.rs_cd = bc.rs_cd
       and rc.rc_seq = bcl.rc_seq
       and rc.effdt = bc.effdt
)
select 'billed_revenue_tax_lean' as case_key,
       count(*) as row_count
  from usage_base ub
  join rc_component_ctx rcx
    on rcx.bseg_id = ub.bseg_id
   and rcx.uom_cd = ub.uom_cd
   and rcx.tou_cd = ub.tou_cd
   and rcx.sqi_cd = ub.sqi_cd;
/

prompt ===== CASE 5: billed_usage_consumption_perf6m =====
select 'billed_usage_consumption_perf6m' as case_key,
       count(*) as row_count
  from cisadm.c1_bi_billed_usage_vw u
 where u.accounting_dt >= trunc(sysdate) - 30
   and u.accounting_dt < trunc(sysdate) + 1
   and u.bill_id is not null
   and u.bseg_id is not null
   and u.rs_cd is not null;
/

prompt ===== CASE 6: billed_usage_consumption_ultralean =====
select 'billed_usage_consumption_ultralean' as case_key,
       count(*) as row_count
  from cisadm.c1_bi_billed_usage_vw u
 where u.accounting_dt >= trunc(sysdate) - 30
   and u.accounting_dt < trunc(sysdate) + 1
   and u.bill_id is not null
   and u.bseg_id is not null
   and u.rs_cd is not null;
/

prompt ===== INDEX INVENTORY (CISADM) =====
select index_name, table_name, column_name, column_position
from all_ind_columns
where table_owner = 'CISADM'
  and table_name in (
    'CI_ACCT','CI_BILL','CI_BSEG','CI_SA',
    'CI_LOOKUP_VAL_L','CI_BILL_CYC_L','CI_CUST_CL_L','CI_COLL_CL_L',
    'CI_RS_L','CI_SA_TYPE_L',
    'CI_BSEG_CALC','CI_BSEG_CALC_LN','CI_RC','CI_RC_L',
    'D1_UOM_L','D1_TOU_L','D1_SQI_L'
  )
order by table_name, index_name, column_position;
/

prompt ===== BENCHMARK COMPLETE =====
