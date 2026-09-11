import { readdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { formatDateTime } from "./format";

/**
 * lib/format.formatDateTime is the app's timestamp format, and it is guarded: null
 * renders "—", an unparseable value renders itself rather than "Invalid Date", and
 * every stamp reads the same way. Five components had re-implemented it as a bare
 * `new Date(x).toLocaleString()`, which has none of that and produces a SECOND format
 * beside the first — audit events, notes and the refresh stamp each rendered
 * differently from the tables next to them.
 *
 * The grep is the point: a helper only removes duplication if nothing quietly
 * reintroduces it.
 */
const COMPONENTS = resolve(__dirname, "../components");

function componentSources(dir: string): Array<[string, string]> {
  const out: Array<[string, string]> = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const path = resolve(dir, entry.name);
    if (entry.isDirectory()) out.push(...componentSources(path));
    else if (entry.name.endsWith(".tsx")) out.push([entry.name, readFileSync(path, "utf8")]);
  }
  return out;
}

describe("timestamp formatting is not re-implemented", () => {
  it("no component builds its own toLocaleString timestamp", () => {
    const offenders = componentSources(COMPONENTS)
      .filter(([, src]) => /new Date\([^)]*\)\.toLocaleString\(\)/.test(src))
      .map(([name]) => name);
    expect(offenders).toEqual([]);
  });
});

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
