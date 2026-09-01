import { describe, expect, it } from "vitest";
import { workspaceScope } from "./workspaceScope";

/**
 * The SQL page said "Query the CISADM schema you know from CIS" to everyone — right for
 * the legacy Oracle path, incomplete for both dbt engines, which reach CISADM AND the
 * reporting canvases beside it.
 *
 * These expectations come from the running fence, not from reading the code: a Postgres
 * org's own rejection message is "The workspace is scoped to cisadm, reporting", and
 * staging/core are refused as internal build layers. An earlier version of this file
 * asserted that a Postgres org should NOT mention CISADM, which was my assumption rather
 * than the system's behaviour, and it produced a sentence just as wrong as the one it
 * replaced.
 */
describe("workspaceScope", () => {
  it("names both schemas on a Postgres warehouse", () => {
    const text = workspaceScope("postgres");
    expect(text).toMatch(/CISADM/);
    expect(text).toMatch(/canvas/i);
  });

  it("names both schemas in the client's own Oracle instance", () => {
    const text = workspaceScope("oracle_dbt");
    expect(text).toMatch(/CISADM/);
    expect(text).toMatch(/ORIGINBA_REPORTING/);
  });

  it("names CISADM alone on the legacy Oracle path, which has no canvases", () => {
    const text = workspaceScope("oracle");
    expect(text).toMatch(/CISADM/);
    expect(text).not.toMatch(/canvas/i);
  });

  it("never promises an internal build layer", () => {
    // staging and core are refused by the fence; offering them would be a broken promise.
    for (const engine of ["postgres", "oracle_dbt", "oracle"] as const) {
      expect(workspaceScope(engine)).not.toMatch(/staging|\bcore\b/i);
    }
  });

  it("is a sentence, for every engine", () => {
    for (const engine of ["postgres", "oracle_dbt", "oracle"] as const) {
      const text = workspaceScope(engine);
      expect(text.length).toBeGreaterThan(20);
      expect(text.trim().endsWith(".")).toBe(true);
    }
  });

  it("promises no schema at all until the engine is known", () => {
    const text = workspaceScope(undefined);
    expect(text).not.toMatch(/CISADM|canvas/i);
    expect(text.trim().endsWith(".")).toBe(true);
  });
});
