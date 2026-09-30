import { describe, expect, it } from "vitest";
import { slowNotice } from "./slowNotice";

// design review 2026-09-29: Letters sat 45-80 s and Data Quality ~60 s behind a silent grey
// block on Ellensburg; a reader cannot tell slow from stuck.
describe("the line under a slow load", () => {
  const what = { doing: "Reading the letters from your CIS database", typical: "a first read can take a minute or more" };
  it("says nothing for the first five seconds", () => {
    expect(slowNotice(4_900, what)).toBeNull();
  });
  it("then says what is happening, how long it usually takes and how long it has taken", () => {
    expect(slowNotice(6_200, what)).toBe("Reading the letters from your CIS database: a first read can take a minute or more (6 s so far).");
    expect(slowNotice(75_000, what)).toBe("Reading the letters from your CIS database: a first read can take a minute or more (1 min 15 s so far).");
  });
});
