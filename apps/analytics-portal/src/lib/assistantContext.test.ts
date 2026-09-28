import { describe, expect, it } from "vitest";
import { contextLabel, explainQuestion, getPageContext, loadTurns, requestAsk, saveTurns, setPageContext, subscribeAsk, subscribePageContext, takeAsk } from "./assistantContext";

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

describe("asking from somewhere else on the page", () => {
  it("a request is taken once, by whichever panel is listening", () => {
    let heard = 0;
    const stop = subscribeAsk(() => { heard += 1; });
    requestAsk({ question: "Explain this", context: null });
    expect(heard).toBe(1);
    expect(takeAsk()?.question).toBe("Explain this");
    expect(takeAsk()).toBeNull();
    stop();
  });

  it("explain-this-number names the figure, its definition and its period", () => {
    const q = explainQuestion({ label: "Payments", subtitle: "Collected on frozen pay segments" }, "$3,660,439.03", "Last 30 days to 18 Jun 2026");
    expect(q).toContain("Payments");
    expect(q).toContain("$3,660,439.03");
    expect(q).toContain("Collected on frozen pay segments");
    expect(q).toContain("Last 30 days to 18 Jun 2026");
  });
});
