import { describe, expect, it } from "vitest";
import { appendTurns, cell, summarise, threadFor, type Turn } from "./assistant";
import type { AssistantResponse } from "./types";

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
