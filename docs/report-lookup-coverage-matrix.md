# Report Lookup Coverage Matrix

This matrix tracks `_CD/_FLG` translation coverage for active reports.
Source of truth:
- `output/workstream_reporting_dictionary.json`
- `Domain Designs.xlsx` (`output/domain_designs_metadata.json`)
- live schema verification in Oracle

## Coverage Status
1. `reports/billing_master.jrxml`
- Implemented: `BILL_STAT_FLG -> BILL_STATUS_DESCR` via `CI_LOOKUP_VAL`
- Implemented: line-item status description via subreport lookup (`BSEG_STAT_FLG`)
- Notes: bill cycle (`BILL_CYC_CD`) remains a filter key and is intentionally shown as code.

2. `reports/subreports/line_items.jrxml`
- Implemented: `BSEG_STAT_FLG -> ITEM_DESCRIPTION` via `CI_LOOKUP_VAL`
- Fallback: `BSEG_STATUS_<code>` when no lookup row exists.

3. `reports/customer_contact_letter.jrxml`
- Implemented: `CC_TYPE_CD -> CC_TYPE_DESCR` via `CI_CC_TYPE_L`
- Implemented: `CC_CL_CD -> CC_CL_DESCR` via `CI_CC_CL_L`
- Implemented: `CONTACT_METH_FLG -> CONTACT_METH_DESCR` via `CI_LOOKUP_VAL`

4. `reports/collections_prioritization.jrxml`
- Implemented: `COLL_CL_CD -> COLL_CL_DESCR` via `CI_COLL_CL_L`
- Notes: `ALERT_TYPE_CD` currently used for count/weight only, not displayed as a detail column.

5. `reports/client_value_scorecard.jrxml`
- No user-facing code columns currently displayed.
- KPI-only output by design.

6. `reports/ops_hub_dashboard.jrxml`
- KPI-only output by design (counts/amounts).
- Code translations are not exposed because detail-level code columns are not rendered.

7. `reports/lookup_description_completeness_audit.jrxml`
- Purpose-built lookup audit report.
- Surfaces domain-level description coverage and missing code samples.
- Use this report to drive remediation in lookup/code tables before client-facing releases.

## SQL Asset Alignment
1. `sql/customer_contact_letter.sql`: aligned with contact code lookups.
2. `sql/collections_prioritization.sql`: aligned with collection class lookup.
3. `sql/c2m_business_use_cases.sql`: use cases updated with lookup enrichment where relevant.

## Known Gaps / Future Enhancements
1. Add detail drilldown reports for alert types with `CI_ALERT_TYPE_L.DESCR80`.
2. Add tender status/type description columns in cashiering presentation reports where user-facing.
3. Add language parameter support instead of hardcoded `'EN'` when multilingual clients require it.

## Validation Commands
1. `python scripts/validate_source_of_truth_sql.py`
2. `python scripts/build_cd_field_inventory.py`
3. `python scripts/check_report_lookup_coverage.py`
4. `python -m pipeline.validate_tables`
