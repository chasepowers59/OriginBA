# CISADM Reporting Gap Assessment

Use this folder to drive read-only discovery of:
- which CISADM configuration tables are actually used in this client environment
- which workstreams are already covered by governed snapshots or Domains
- which reporting questions still rely on fragile raw-table joins
- which new snapshots, Topics, Domains, or report-side SQL are still needed

## Workflow
1. Run [01_candidate_configuration_tables.sql](/C:/Users/cvpow/OneDrive/Desktop/OriginBA/sql/reporting_assessment/01_candidate_configuration_tables.sql) to identify configuration and lookup tables present in this CISADM schema.
2. Run [02_transactional_value_inventory.sql](/C:/Users/cvpow/OneDrive/Desktop/OriginBA/sql/reporting_assessment/02_transactional_value_inventory.sql) to see which business codes are actually active in current transactional data.
3. Fill out [03_workstream_coverage_matrix.md](/C:/Users/cvpow/OneDrive/Desktop/OriginBA/docs/reporting_gap_assessment/03_workstream_coverage_matrix.md).
4. Summarize approved findings and next actions in [04_reporting_gap_findings.md](/C:/Users/cvpow/OneDrive/Desktop/OriginBA/docs/reporting_gap_assessment/04_reporting_gap_findings.md).

## Main questions to answer
- Which workstreams still lack a governed reporting layer?
- Which client-specific configuration values materially change join logic, naming, or filter semantics?
- Which reports should use raw Domain tables, and which need Oracle-side snapshots first?
- Which lookup or type tables are required to keep descriptions and business semantics accurate?
- Which source tables are too large or too mixed-grain for safe self-service use?

## Expected outputs
- workstream coverage matrix
- active configuration inventory by workstream
- missing governed artifact backlog
- candidate snapshot list with grain and driving population
- repeatable notes for future skill updates
