import type { WorkspaceEngine } from "./databaseQueryTemplates";

/** ci_pay_tndr carries protected columns, so its browse lists safe columns; the fence rejects SELECT * there. */
const TENDER_COLUMNS = "pay_event_id, tender_type_cd, tender_amt, tender_ctl_id";

/**
 * The browse query "Open in SQL →" and the Tables tab seed for a table, in the engine's own
 * dialect: Postgres reads CISADM and the data sets through one search path and takes LIMIT;
 * an Oracle in-database organization runs with CURRENT_SCHEMA=CISADM, reaches a data set as
 * ORIGINBA_REPORTING.<name>, and takes FETCH FIRST. Seeded only once the engine is known.
 */
export function browseQuery(tableName: string, engine: WorkspaceEngine, pageSize: number): string {
  const name = tableName.toLowerCase();
  const cols = name === "ci_pay_tndr" ? TENDER_COLUMNS : "*";
  if (engine === "postgres") return `SELECT ${cols}\nFROM cisadm.${name}\nLIMIT ${pageSize}`;
  const from = engine === "oracle_dbt" && name.startsWith("rpt_") ? `originba_reporting.${name}` : name;
  return `SELECT ${cols}\nFROM ${from}\nFETCH FIRST ${pageSize} ROWS ONLY`;
}
