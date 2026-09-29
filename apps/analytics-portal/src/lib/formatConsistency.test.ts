import { describe, expect, it } from "vitest";
import { formatDateTime } from "./format";

/**
 * lib/format.formatDateTime is the app's timestamp format, and it is guarded: null
 * renders "—", an unparseable value renders itself rather than "Invalid Date". Five
 * components had re-implemented it as a bare `new Date(x).toLocaleString()`, a SECOND
 * format beside the first; format.test.ts now greps every source file for that.
 */
describe("formatDateTime", () => {
  it("renders an em dash for nothing, rather than Invalid Date", () => {
    expect(formatDateTime(null)).toBe("—");
    expect(formatDateTime(undefined)).toBe("—");
    expect(formatDateTime("")).toBe("—");
  });

  it("echoes an unparseable value instead of Invalid Date", () => {
    expect(formatDateTime("not a date")).toBe("not a date");
  });

  it("formats a real timestamp", () => {
    const out = formatDateTime("2026-09-02T12:34:00Z");
    expect(out).toMatch(/2026/);
    expect(out).not.toMatch(/Invalid/);
  });

  it("accepts a Date, which is what the print headers pass", () => {
    expect(formatDateTime(new Date("2026-09-02T12:34:00Z"))).toMatch(/2026/);
  });
});
