# Archived from sql/performance/snapshots/debt_mgmt/ (2026-09-08)

| item | now at | why |
| --- | --- | --- |
| `sa_aged_bal` | `archive/2026-09-08_reorg/sql/performance/snapshots/debt_mgmt/sa_aged_bal` | consolidation snapshot: designed 2026-06-11 (cbc1357), never deployed to a client |
| `wo_proc` | `archive/2026-09-08_reorg/sql/performance/snapshots/debt_mgmt/wo_proc` | consolidation snapshot: designed 2026-06-11 (cbc1357), never deployed to a client |
| `acct_debt` | `archive/2026-09-08_reorg/sql/performance/snapshots/debt_mgmt/acct_debt` | governed-but-separate snapshot, outside the active-8 stagger since 2026-04; QA and master guide never written |
| `coll_proc` | `archive/2026-09-08_reorg/sql/performance/snapshots/debt_mgmt/coll_proc` | governed-but-separate snapshot, outside the active-8 stagger since 2026-04; QA and master guide never written |

Index: `archive/2026-09-08_reorg/INDEX.md`.
| `00a_config_discovery_validation.sql` | `archive/2026-09-08_reorg/sql/performance/snapshots/debt_mgmt/00a_config_discovery_validation.sql` | discovery pack for building ACCT_DEBT, COLL_PROC, PA_RQST and WO_PROC snapshots, all archived; CMS_SA_SNAPSHOT (active) has its own deployment under cms_sa_snapshot/ |
