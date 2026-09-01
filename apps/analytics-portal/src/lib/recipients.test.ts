import { describe, expect, it } from "vitest";
import { parseRecipients } from "./recipients";

/** Both the schedule and alert dialogs take one free-text recipient field; this
 *  is the one parser they share. */
describe("parseRecipients", () => {
  it("splits on commas, semicolons and whitespace", () => {
    expect(parseRecipients("a@x.gov, b@x.gov; c@x.gov\nd@x.gov")).toEqual([
      "a@x.gov",
      "b@x.gov",
      "c@x.gov",
      "d@x.gov",
    ]);
  });

  it("drops empties and surrounding whitespace", () => {
    expect(parseRecipients("  a@x.gov ,, ")).toEqual(["a@x.gov"]);
    expect(parseRecipients("   ")).toEqual([]);
    expect(parseRecipients("")).toEqual([]);
  });
});
