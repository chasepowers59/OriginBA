import { describe, expect, it } from "vitest";
import { clientLogo } from "./branding";

describe("co-branding", () => {
  it("a client's own logo sits beside Origin's", () => {
    expect(clientLogo({ brand: { logo_src: "/clients/newark.png" } })).toBe("/clients/newark.png");
  });

  it("Origin's own marks are not shown twice", () => {
    for (const src of ["/origin-mark.png", "/origin-logo.png", "/brand-icon.svg", ""]) {
      expect(clientLogo({ brand: { logo_src: src } })).toBeNull();
    }
    expect(clientLogo(null)).toBeNull();
  });
});
