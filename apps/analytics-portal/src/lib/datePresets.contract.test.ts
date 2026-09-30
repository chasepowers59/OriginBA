import { describe, expect, it } from "vitest";
import fs from "node:fs";
import path from "node:path";
import { applyDatePresetConfig } from "./datePresets";
import type { DatePresetConfig } from "./types";

// Shared with the server (tests/test_date_presets.py): the cache warmer rebuilds these windows.
const { cases } = JSON.parse(fs.readFileSync(path.join(__dirname, "../../../../tests/fixtures/date_presets.json"), "utf8")) as {
  cases: { preset: DatePresetConfig | string | null; as_of: string; range: [string, string]; label?: string }[];
};

describe("explorer opening windows match the server's", () => {
  for (const c of cases) {
    it(`${JSON.stringify(c.preset)} as of ${c.as_of}`, () => {
      const out = applyDatePresetConfig(c.preset ?? undefined, c.as_of);
      expect(out.range).toEqual(c.range);
      if (c.label) expect(out.label).toBe(c.label);
    });
  }
});
