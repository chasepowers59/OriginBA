import { describe, expect, it } from "vitest";
import { browseQuery } from "./databaseBrowse";

/**
 * "Open in SQL →" on a data set page seeds a browse query. On 2026-10-02 CityCorp (Oracle,
 * in-database) got the Postgres form, `SELECT * FROM cisadm.rpt_payment LIMIT 50`, and Run
 * answered ORA-00907: the page seeded on mount, before it had learned its engine. The query
 * is a pure function of table, engine and page size, and the page seeds once the engine is known.
 */
describe("browseQuery: the seed query for a table, in the engine's own dialect", () => {
  it("Postgres: the CISADM schema and LIMIT", () => {
    expect(browseQuery("rpt_payment", "postgres", 50)).toBe("SELECT *\nFROM cisadm.rpt_payment\nLIMIT 50");
    expect(browseQuery("ci_sa", "postgres", 100)).toBe("SELECT *\nFROM cisadm.ci_sa\nLIMIT 100");
  });

  it("Oracle in-database: a data set is in ORIGINBA_REPORTING, a CISADM table is unqualified, and FETCH FIRST", () => {
    expect(browseQuery("rpt_payment", "oracle_dbt", 50)).toBe("SELECT *\nFROM originba_reporting.rpt_payment\nFETCH FIRST 50 ROWS ONLY");
    expect(browseQuery("ci_sa", "oracle_dbt", 50)).toBe("SELECT *\nFROM ci_sa\nFETCH FIRST 50 ROWS ONLY");
  });

  it("the tender table lists its safe columns, never *, on either engine", () => {
    expect(browseQuery("ci_pay_tndr", "postgres", 50)).toBe("SELECT pay_event_id, tender_type_cd, tender_amt, tender_ctl_id\nFROM cisadm.ci_pay_tndr\nLIMIT 50");
    expect(browseQuery("CI_PAY_TNDR", "oracle_dbt", 50)).toContain("pay_event_id, tender_type_cd, tender_amt, tender_ctl_id");
  });
});
