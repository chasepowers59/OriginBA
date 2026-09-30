import { describe, expect, it } from "vitest";
import { embedLink, embedSnippet, EMBED_LIFETIMES } from "./embed";

describe("embed links", () => {
  it("points at the portal's embed page", () => {
    expect(embedLink("https://portal.test", "a.b.c")).toBe("https://portal.test/embed/a.b.c");
  });

  it("gives an iframe that another site can paste, with a title for screen readers", () => {
    const html = embedSnippet("https://portal.test", "a.b.c", "Billed by cycle");
    expect(html).toBe(
      '<iframe src="https://portal.test/embed/a.b.c" title="Billed by cycle" width="100%" height="480" style="border:0"></iframe>',
    );
  });

  it("escapes the title so a view name cannot break out of the attribute", () => {
    expect(embedSnippet("https://p.test", "t", 'A "quoted" <b>')).toContain('title="A &quot;quoted&quot; &lt;b&gt;"');
  });

  it("offers lifetimes no longer than the API's one-day cap", () => {
    expect(Math.max(...EMBED_LIFETIMES.map((l) => l.minutes))).toBeLessThanOrEqual(24 * 60);
  });
});
