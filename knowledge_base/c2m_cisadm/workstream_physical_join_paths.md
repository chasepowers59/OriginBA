# Workstream Physical Join Paths (9 Workstreams)

Physical CISADM tables only. Do **not** use custom views (`CMS_*`, `*_VW`) in governed SQL or Domain-derived tables. Enrichment uses **LEFT JOIN** so the driving population is preserved.

Machine-readable sources:
- `output/workstream_physical_catalog.json` — tables per workstream
- `output/workstream_physical_join_paths.json` — canonical chains + domain-inferred joins
- `output/cisadm_dictionary/fk_join_map_full.csv` — deduped join keys

Regenerate:
```bash
python3 scripts/build_workstream_physical_catalog.py
python3 scripts/build_fk_join_map_full.py
python3 scripts/build_ai_cisadm_context.py --client demo
```

---

## SQL rules (all workstreams)

1. Pick the **driver table** that matches business grain (see chains below).
2. Join optional lookup `_L`, char, and detail tables with **LEFT JOIN**.
3. Use `LANGUAGE_CD = 'ENG'` on label tables.
4. Use `NULLIF(TRIM(code_col),'')` for C2M blank-string codes.
5. Validate row counts after each major join.

---

## 1. Billing and Rates (`billing`)

**Driver:** `CI_BSEG` (bill segment facts) or `CI_SA` (expected population)

**Core chain:**
```sql
FROM cisadm.ci_bseg bseg
INNER JOIN cisadm.ci_sa sa ON sa.sa_id = bseg.sa_id
INNER JOIN cisadm.ci_acct acct ON acct.acct_id = sa.acct_id
LEFT JOIN cisadm.ci_bill bill ON bill.bill_id = bseg.bill_id
```

**Common LEFT enrichments:** `CI_BSEG_SQ`, `CI_BSEG_READ`, `CI_BSEG_CALC`, `CI_BSEG_CALC_LN`, `CI_BSEG_ITEM`, `CI_BSEG_EXCP`, `CI_ACCT_PER`, `CI_PER_NAME`, `CI_BILL_CYC_L`, `CI_LOOKUP_VAL_L`

---

## 2. Cashiering (`cashiering`)

**Driver:** `CI_PAY_EVENT` or `CI_PAY`

```sql
FROM cisadm.ci_pay_event pe
LEFT JOIN cisadm.ci_pay pay ON pay.pay_event_id = pe.pay_event_id
LEFT JOIN cisadm.ci_acct acct ON acct.acct_id = pay.acct_id
LEFT JOIN cisadm.ci_pay_tndr tndr ON tndr.pay_id = pay.pay_id
LEFT JOIN cisadm.ci_pay_seg pseg ON pseg.pay_id = pay.pay_id
```

---

## 3. Meter Operations (`meter_ops`)

**Usage driver:** `D1_USAGE` or `C1_USAGE`

```sql
FROM cisadm.d1_usage du
LEFT JOIN cisadm.c1_usage cu ON cu.usage_id = du.usg_ext_id
LEFT JOIN cisadm.ci_sa sa ON sa.sa_id = cu.sa_id
LEFT JOIN cisadm.ci_acct acct ON acct.acct_id = sa.acct_id
LEFT JOIN cisadm.d1_usage_scalar_dtl sq ON sq.d1_usage_id = du.d1_usage_id
```

**Device driver:** `D1_INSTALL_EVT` or `CI_SP`

```sql
FROM cisadm.ci_sp sp
LEFT JOIN cisadm.d1_install_evt inst ON inst.d1_sp_id = sp.sp_id
LEFT JOIN cisadm.d1_dvc_cfg cfg ON cfg.d1_device_id = inst.d1_device_id
LEFT JOIN cisadm.d1_dvc dvc ON dvc.d1_device_id = cfg.d1_device_id
```

---

## 4. Customer Operations (`customer_ops`)

**Account driver:** `CI_ACCT`

```sql
FROM cisadm.ci_acct acct
LEFT JOIN cisadm.ci_acct_per ap ON ap.acct_id = acct.acct_id AND ap.main_cust_sw = 'Y'
LEFT JOIN cisadm.ci_per per ON per.per_id = ap.per_id
LEFT JOIN cisadm.ci_per_name pn ON pn.per_id = ap.per_id AND pn.name_type_flg = 'PRIM'
```

**Case driver:** `CI_CASE`

```sql
FROM cisadm.ci_case cs
LEFT JOIN cisadm.ci_acct acct ON acct.acct_id = cs.acct_id
LEFT JOIN cisadm.ci_prem prem ON prem.prem_id = cs.prem_id
LEFT JOIN cisadm.ci_per_name case_person ON case_person.per_id = cs.per_id AND case_person.name_type_flg = 'PRIM'
```

---

## 5. New Services and Planning (`new_services`)

**Driver:** `CI_SA`

```sql
FROM cisadm.ci_sa sa
LEFT JOIN cisadm.ci_acct acct ON acct.acct_id = sa.acct_id
LEFT JOIN cisadm.ci_sa_sp sas ON sas.sa_id = sa.sa_id
LEFT JOIN cisadm.ci_sp sp ON sp.sp_id = sas.sp_id
LEFT JOIN cisadm.ci_sa_type sat ON sat.cis_division = sa.cis_division AND sat.sa_type_cd = sa.sa_type_cd
```

Use LEFT JOIN to `CI_SA_SP` to find SAs **without** a service point.

---

## 6. Finance (`finance`)

**Driver:** `CI_FT`

```sql
FROM cisadm.ci_ft ft
LEFT JOIN cisadm.ci_sa sa ON sa.sa_id = ft.sa_id
LEFT JOIN cisadm.ci_acct acct ON acct.acct_id = sa.acct_id
LEFT JOIN cisadm.ci_ft_gl ftgl ON ftgl.ft_id = ft.ft_id
LEFT JOIN cisadm.ci_ft_proc ftp ON ftp.ft_id = ft.ft_id
```

Governed arrears slice: `ft.freeze_sw = 'Y' AND ft.not_in_ars_sw = 'N' AND ft.ft_type_flg NOT IN ('PS','PX') AND ft.ars_dt IS NOT NULL`

---

## 7. Debt Management (`debt_mgmt`)

**Driver:** `CI_FT` (debt amounts) — not collection workflow alone

```sql
FROM cisadm.ci_ft ft
LEFT JOIN cisadm.ci_sa sa ON sa.sa_id = ft.sa_id
LEFT JOIN cisadm.ci_acct acct ON acct.acct_id = sa.acct_id
LEFT JOIN cisadm.ci_coll_proc coll ON coll.acct_id = acct.acct_id
LEFT JOIN cisadm.c1_pa_rqst pa ON pa.acct_id = acct.acct_id
```

---

## 8. Field Operations (`field_ops`)

**Driver:** `D1_ACTIVITY` (join `D1_ACTIVITY_TYPE` where `ACTIVITY_TYPE_CAT_FLG = 'D1FA'`)

```sql
FROM cisadm.d1_activity act
INNER JOIN cisadm.d1_activity_type act_type
  ON act_type.activity_type_cd = act.activity_type_cd
 AND act_type.activity_type_cat_flg = 'D1FA'
LEFT JOIN cisadm.d1_activity_char ach ON ach.d1_activity_id = act.d1_activity_id
LEFT JOIN cisadm.d1_activity_rel rel ON rel.d1_activity_id = act.d1_activity_id
LEFT JOIN cisadm.ci_sa_sp sas ON sas.sp_id = rel.pk_value1  -- when rel links to SP
LEFT JOIN cisadm.c1_representative rep ON rep.c1_representative_cd = ach.srch_char_val  -- when char links crew
```

Includes field tasks: `F1_TSK`, `F1_TSK_LOG` (LEFT JOIN from activity or SP context).

---

## 9. Common (`common`)

**Workflow driver:** `CI_TD_ENTRY` / `CI_BATCH_INST`

**Premise driver:** `CI_PREM`

```sql
FROM cisadm.ci_prem prem
LEFT JOIN cisadm.ci_prem_char pch ON pch.prem_id = prem.prem_id
LEFT JOIN cisadm.ci_sp sp ON sp.prem_id = prem.prem_id
```

---

## Population checks

Before using a table on a client:
```bash
python3 scripts/local/run_all_clients_table_health.sh
```

Inspect `deploy/snapshot_rollout_logs/<client>/table_health.json` or `output/ai_cisadm_context.json` (`client_health.population_status`).

| Status | Meaning |
|--------|---------|
| `populated` | Table exists with rows |
| `empty` | Table exists, zero rows |
| `missing` | Not in CISADM on that client |

Do not drive ad hoc Domains from `empty` or `missing` tables without documenting the gap.
