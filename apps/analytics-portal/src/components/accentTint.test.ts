import { readFileSync } from "node:fs";
import { readdirSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

/**
 * Soul Palette V2.1 rewrote the reference app's translucent tints onto token colours
 * and silently dropped their alpha, because Tailwind cannot apply an opacity modifier
 * to a raw `var()` -- `from-sky-500/10` became `from-primary`, which is fully opaque.
 * Nine surfaces that were meant to be a 5-40% wash turned into solid dark-blue blocks
 * with their original dark text still on top. Measured live on /explore/rpt_bill_segment
 * before the fix:
 *
 *   "27.1%"              text-primary  #006fac on the #006fac stop   1.00:1  invisible
 *   "Electric Commercial" text-heading #1b2530 on #1348AB            1.88:1
 *   "Combined total"      text-fg-muted #56636e on #1348AB           1.14:1
 *
 * Any `bg-gradient-*` built from an accent/primary TOKEN is opaque by construction, so
 * the class itself is the defect -- there is no correct way to write this in Tailwind.
 * The tint utilities in globals.css carry the weight with color-mix instead.
 */
const COMPONENTS = resolve(__dirname);

function sources(): Array<[string, string]> {
  return readdirSync(COMPONENTS)
    .filter((f) => f.endsWith(".tsx"))
    .map((f) => [f, readFileSync(resolve(COMPONENTS, f), "utf8")]);
}

describe("accent tint surfaces", () => {
  it("never builds a gradient from an opaque accent token", () => {
    const offenders = sources()
      .filter(([, src]) => /bg-gradient-to-[a-z]+[^"'`]*\b(?:from|via|to)-(?:primary|accent)\b/.test(src))
      .map(([name]) => name);
    expect(offenders).toEqual([]);
  });

  it("still tints those surfaces rather than dropping the treatment", () => {
    const tinted = sources().filter(([, src]) => /\btint-(?:panel|active|rule|header)/.test(src));
    expect(tinted.length).toBeGreaterThanOrEqual(6);
  });
});
