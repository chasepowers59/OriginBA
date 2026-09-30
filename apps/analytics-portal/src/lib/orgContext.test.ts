import { describe, expect, it } from "vitest";
import { viewingAnotherClient } from "./orgContext";

describe("viewing another client", () => {
  it("is true only when an organization is chosen and it is not the person's own", () => {
    expect(viewingAnotherClient("ellensburg", "demo25")).toBe(true);
    expect(viewingAnotherClient("demo25", "demo25")).toBe(false);
    expect(viewingAnotherClient(null, "demo25")).toBe(false);
    expect(viewingAnotherClient("", null)).toBe(false);
    // an admin has no home organization: any chosen client is "another" one
    expect(viewingAnotherClient("ellensburg", null)).toBe(true);
  });
});
