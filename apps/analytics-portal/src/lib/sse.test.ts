import { describe, expect, it } from "vitest";
import { parseSse, stepLabel } from "./sse";

describe("reading the assistant's event stream", () => {
  it("splits complete events and keeps a partial one for the next chunk", () => {
    const first = parseSse('event: step\ndata: {"tool":"run_sql","detail":"billed by cycle"}\n\nevent: step_do');
    expect(first.events).toEqual([{ type: "step", data: { tool: "run_sql", detail: "billed by cycle" } }]);
    const second = parseSse(first.rest + 'ne\ndata: {"tool":"run_sql","ok":true,"rows":10}\n\n');
    expect(second.events).toEqual([{ type: "step_done", data: { tool: "run_sql", ok: true, rows: 10 } }]);
    expect(second.rest).toBe("");
  });

  it("names each step the way a person would", () => {
    expect(stepLabel({ tool: "list_canvases" })).toBe("Finding the right report");
    expect(stepLabel({ tool: "describe_canvas", detail: "rpt_bill_segment" })).toBe("Reading rpt_bill_segment");
    expect(stepLabel({ tool: "run_sql", detail: "billed by cycle" })).toBe("Running: billed by cycle");
    expect(stepLabel({ tool: "verification_status" })).toBe("Checking how far the figures can be trusted");
  });
});
