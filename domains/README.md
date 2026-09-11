# Domains

Rewritten 2026-09-08. Two kinds of domain, two homes:

- **Generated** from the dbt reporting canvases: `~/originba_dbt/jaspersoft/domains/<target>/` (never hand-edited; item ids from `~/originba_dbt/scripts/bi_names.py`).
- **Hand-built** over CISADM or the active-8 snapshot tables: here.

| Path | What it holds | Rule |
| --- | --- | --- |
| `exports/manual_imports/` | the seven active-8 snapshot domains (`FT`, `FT_GL_DISTRIBUTION`, `BSEG_BILLED_USAGE`, `BSEG_SQ_USAGE`, `D1_MSRMT`, `D1_USAGE`, `D1_USAGE_SCALAR_DTL`, each as *_RPT_CURR_End_User_Friendly.xml), the retained import bundles (`FinalDomain.zip`, `New Bill Cycle Domain.zip`, `New Export Billing.zip`) and `exports/manual_imports/current_snapshot_report_packages/` | import-ready; `CMS_SA_SNAPSHOT` is served by the Standard Offering package's `SA_Snapshot___Aged_Balance` domain, not a file here |
| `manual_imports/newark_*` | Newark client deliverables (REP8 aged balance domain and report, account aged balance), each regenerated from its `schema.reference.xml` by `scripts/jaspersoft/build_newark_*.py` | a coupled unit with `sql/clients/newark/`; never moved by tooling |
| `working/` | temporary extraction and editing area (`billing_requirements_domain_v2`, `new_bill_cycle_domain`) | nothing here is production-safe |
| `archive/2026-09-08_reorg/domains/` | the 15 domain XMLs over snapshots that were never deployed or are retired, and the 2026-04-28 manual designs | history |

Validation: `scripts/jaspersoft/validate_domain_schema.py` (SL XMLSchema 1.3). Format contract and
import-and-verify protocol: `~/originba_dbt/.claude/skills/jaspersoft-domain-generation/SKILL.md`;
modeling rules for hand-built domains: `.claude/skills/originba-jaspersoft-domain-modeling/SKILL.md`.
