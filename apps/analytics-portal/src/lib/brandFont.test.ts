import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

/**
 * Brand font: Aptos (Origin's chosen face, Microsoft's M365 default). It is not a
 * Google Font and its files ship with M365, so the app PREFERS locally-installed
 * Aptos and falls back to the bundled Inter — every Microsoft-shop utility user gets
 * Aptos natively, everyone else gets a clean fallback. These tests pin the stack so
 * a refactor can't silently drop the brand face.
 */
describe("brand font stack", () => {
  const css = readFileSync(join(__dirname, "../app/globals.css"), "utf8");
  const layout = readFileSync(join(__dirname, "../app/layout.tsx"), "utf8");

  it("body font-family leads with Aptos", () => {
    const m = css.match(/body\s*\{[\s\S]*?font-family:\s*([^;]+);/);
    expect(m, "globals.css must declare the body font-family").toBeTruthy();
    const stack = m![1];
    expect(stack.trim().startsWith('"Aptos"')).toBe(true);
    expect(stack).toContain("var(--font-inter)"); // bundled fallback
    expect(stack).toContain("system-ui"); // last-resort system stack
  });

  it("layout exposes Inter as a CSS variable, not a hard body class", () => {
    expect(layout).toContain('variable: "--font-inter"');
    expect(layout).not.toMatch(/inter\.className/);
  });
});
