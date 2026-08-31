/**
 * One-line guides for the core CISADM tables, shown in the SQL workspace's Tables tab.
 * The audience is a utility analyst who knows CIS — the guide is orientation ("which of
 * these 200 tables is the one I want"), not documentation. Keys are matched
 * case-insensitively so the Postgres landing (lowercase) and Oracle (uppercase) agree.
 */
const GUIDE: Record<string, string> = {
  ci_acct: "Account master — one row per account.",
  ci_acct_per: "Account ↔ person links — who is on the account, main customer flag.",
  ci_per: "Person master (names live in ci_per_name).",
  ci_per_name: "Person names; prim_name_sw = 'Y' is the display name.",
  ci_sa: "Service agreement — the billable service contract; sa_status_flg is lifecycle.",
  ci_sa_sp: "SA ↔ service point links.",
  ci_sp: "Service point — where service is delivered.",
  ci_prem: "Premise — the physical location an SP sits at.",
  ci_bill: "Bill header — one row per bill; bill_stat_flg 'C' = complete.",
  ci_bseg: "Bill segment — one SA's charges on a bill; bseg_stat_flg 50 = frozen.",
  ci_bseg_calc: "Bill segment calc headers (one per rate application).",
  ci_bseg_calc_ln: "Calc lines — the actual billed charge amounts.",
  ci_bseg_sq: "Billed service quantities — usage by UOM/TOU/SQI.",
  ci_bseg_read: "Reads consumed by a bill segment.",
  ci_ft: "Financial transaction — every dollar movement; freeze_sw = 'Y' when frozen.",
  ci_ft_gl: "FT general-ledger distribution lines.",
  ci_pay: "Payment (per SA slice of a payment event).",
  ci_pay_event: "Payment event — groups the tenders that funded the payments.",
  ci_pay_tndr: "Payment tender — how it was paid. Protected columns; list columns explicitly.",
  ci_pay_seg: "Payment segments — the FT-bearing pieces of a payment.",
  ci_adj: "Adjustment — non-bill, non-pay dollar changes.",
  ci_to_do_entry: "To-do entries — the CIS work queue.",
  ci_cc: "Customer contact — every logged interaction.",
  ci_cust_cl: "Customer class codes (join ci_cust_cl_l for the English label).",
  ci_sa_type: "SA type configuration per CIS division.",
  ci_prem_type: "Premise type codes.",
  d1_msrmt: "Measurement (MDM) — device reads after VEE.",
  d1_usage: "Usage transaction — processed usage sent to billing.",
  d1_dvc: "Device (meter) master.",
  d1_dvc_cfg: "Device configuration — the measuring setup on a device.",
  d1_sp: "MDM service point mirror of ci_sp.",
  d1_install_evt: "Install event — device on/off history at a service point.",
  f1_bkt_alg: "Framework bucket algorithms (aging buckets).",
};

export function cisadmTableGuide(tableName: string): string | null {
  return GUIDE[tableName.toLowerCase()] ?? null;
}
