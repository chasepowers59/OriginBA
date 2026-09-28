import { describe, expect, it } from "vitest";
import { contextLabel, getPageContext, loadTurns, saveTurns, setPageContext, subscribePageContext } from "./assistantContext";

describe("the page the assistant is asked from", () => {
  it("is published by the page and heard by the panel", () => {
    let heard = 0;
    const stop = subscribePageContext(() => { heard += 1; });
    setPageContext({ canvas_id: "rpt_bill_segment", label: "Bill Segment", period: "Last 180 days" });
    expect(getPageContext()?.canvas_id).toBe("rpt_bill_segment");
    setPageContext(null);
    stop();
    setPageContext({ canvas_id: "rpt_gl", label: "General Ledger" });
    expect(heard).toBe(2);
    setPageContext(null);
  });

  it("reads as the page's own name and period", () => {
    expect(contextLabel({ canvas_id: "rpt_bill_segment", label: "Bill Segment", period: "Last 180 days" }))
      .toBe("Bill Segment · Last 180 days");
    expect(contextLabel({ canvas_id: "rpt_gl", label: "General Ledger" })).toBe("General Ledger");
  });
});

describe("the conversation survives moving between pages", () => {
  it("round-trips through session storage, and an unusable store is an empty conversation", () => {
    const store = new Map<string, string>();
    const storage = { getItem: (k: string) => store.get(k) ?? null, setItem: (k: string, v: string) => void store.set(k, v) };
    saveTurns([{ role: "user", text: "hi" }], storage);
    expect(loadTurns(storage)).toEqual([{ role: "user", text: "hi" }]);
    expect(loadTurns({ getItem: () => "{not json", setItem: () => undefined })).toEqual([]);
    expect(loadTurns(undefined)).toEqual([]);
  });
});
