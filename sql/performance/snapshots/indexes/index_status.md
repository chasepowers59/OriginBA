# Snapshot Index Status

| Snapshot Table | Index Name | Status | Filter Pattern | Notes |
|---|---|---|---|---|
| `FT_GL_DISTRIBUTION_RPT_CURR` | `XOBA_FTGLRPT_FT_ADJSTAT_ACCTDT` | Active | `FT_TYPE_FLG + ADJ_STATUS_FLG + ACCOUNTING_DT` | Created and accepted as the current GL adjustment-report index. |
| `FT_RPT_CURR` | `XOBA_FTRPT_FT_ACCTDT` | Active | `FT_TYPE_FLG + ACCOUNTING_DT` | Accepted as the current FT snapshot index for the common FT report filter pattern. |
