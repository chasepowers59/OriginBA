import { describe, expect, it } from "vitest";
import { runLine } from "./scheduleHistory";

describe("schedule run history", () => {
  it("reads as one line per run", () => {
    expect(runLine({ at: "2026-09-01T13:05:00+00:00", trigger: "schedule", status: "sent", rows: 120 }, (s) => `@${s}`))
      .toBe("@2026-09-01T13:05:00+00:00 · scheduled · sent, 120 rows");
    expect(runLine({ at: "2026-09-02T09:00:00+00:00", trigger: "send now", status: "error: warehouse down", rows: null }, (s) => s))
      .toBe("2026-09-02T09:00:00+00:00 · Send now · error: warehouse down");
  });
});
