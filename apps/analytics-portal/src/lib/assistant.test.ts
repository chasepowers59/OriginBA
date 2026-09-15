import { describe, expect, it } from "vitest";
import { ageLabel, appendTurns, cell, integrityHeadline, integrityLabel, summarise, threadFor, type Turn } from "./assistant";
import type { AssistantResponse, CanvasIntegrity, IntegrityOverview } from "./types";

const answer = (thread: unknown[] = []): AssistantResponse => ({
  answer: "42", steps: [{ tool: "run_sql", input: "{}", ok: true }],
  queries: [{ purpose: "p", sql: "select 1", columns: ["n"], rows: [[42]], row_count: 1, truncated: false, ms: 3 }],
  model: "m", usage: { input_tokens: 1000, output_tokens: 240 }, thread: thread as AssistantResponse["thread"],
});

describe("the assistant conversation", () => {
  it("keeps question and answer as a pair", () => {
    const turns = appendTurns([], "how many?", answer());
    expect(turns.map((t) => t.role)).toEqual(["user", "assistant"]);
  });

  it("sends the API's own thread from the last answer, and nothing before the first", () => {
    expect(threadFor([])).toEqual([]);
    const turns: Turn[] = [
      { role: "user", text: "a" }, { role: "assistant", response: answer([{ role: "user", content: "a" }]) },
      { role: "user", text: "b" }, { role: "error", text: "boom" },
    ];
    expect(threadFor(turns)).toEqual([{ role: "user", content: "a" }]);
  });

  it("summarises an answer in words a reader scans", () => {
    expect(summarise(answer())).toBe("1 step · 1 query · 1,240 tokens");
    expect(summarise({ ...answer(), steps: [], queries: [], usage: { input_tokens: 0, output_tokens: 0 } })).toBe("0 steps · 0 queries");
  });

  it("formats cells like the rest of the portal, and never a year with a comma", () => {
    expect(cell(null, "Rows")).toBe("—");
    expect(cell(12345, "Rows")).toBe("12,345");
    expect(cell("CYCLE1", "Bill Cycle")).toBe("CYCLE1");
    expect(cell(2026, "Year")).toBe("2026");
    expect(cell(3837610416, "Account ID")).toBe("3837610416");
  });
});

describe("what a figure can be trusted to", () => {
  const now = new Date("2026-09-15T12:00:00");
  const proven: CanvasIntegrity = {
    canvas: "rpt_sa_aged_balance", verdict: "proven", canvas_as_of: "2026-09-09T12:32:41",
    summary: "12/12 checks vs CISADM; 138,086 rows vs CMS_SA_SNAPSHOT, 0 differ",
  };

  it("names the canvas, the proof and the build age", () => {
    expect(integrityLabel({ ...proven })).toMatch(/^rpt_sa_aged_balance: proven \(12\/12 checks vs CISADM; 138,086 rows vs CMS_SA_SNAPSHOT, 0 differ\) · built /);
  });

  it("says plainly when nothing is on record", () => {
    expect(integrityLabel({ canvas: "rpt_x", verdict: "unavailable", canvas_as_of: null, summary: "" })).toBe("rpt_x: no verification on record");
    expect(integrityLabel({ canvas: "rpt_x", verdict: "not covered", canvas_as_of: null, summary: "" })).toBe("rpt_x: not covered by a parity check");
  });

  it("ages a build in hours, then days", () => {
    expect(ageLabel("2026-09-15T11:30:00", now)).toBe("within the hour");
    expect(ageLabel("2026-09-14T20:00:00", now)).toBe("16 h ago");
    expect(ageLabel("2026-09-09T12:32:41", now)).toBe("5 days ago");
  });

  it("headlines the build age and the proven count", () => {
    const o: IntegrityOverview = {
      available: true, canvas_as_of: "2026-09-09T12:32:41",
      canvases: [
        { canvas: "a", verdict: "proven", source_green: 3, source_checks: 3, snapshot_against: null, snapshot_ok: null },
        { canvas: "b", verdict: "differences", source_green: 1, source_checks: 3, snapshot_against: "FT_RPT_CURR", snapshot_ok: true },
      ],
    };
    expect(integrityHeadline(o, now)).toBe("Canvases built 5 days ago · 1 of 2 canvases proven against the source database");
    expect(integrityHeadline({ available: false, canvases: [] }, now)).toBe("No verification on record for this organization yet.");
  });
});
