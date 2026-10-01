import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import NotFound from "./not-found";
import RouteError from "./error";

// A mistyped link or a page that throws must leave the reader somewhere they can act from,
// not on the framework's bare 404 or "Application error" screen (2026-10-01 QA).
describe("fallback pages", () => {
  it("not-found says so and offers the way back", () => {
    const html = renderToStaticMarkup(<NotFound />);
    expect(html).toContain("Page not found");
    expect(html).toContain('href="/"');
    expect(html).toContain('href="/reports"');
  });

  it("a page error offers a retry and home, and the reference to quote", () => {
    const err = Object.assign(new Error("boom: ORA-00942 internal detail"), { digest: "abc123" });
    const html = renderToStaticMarkup(<RouteError error={err} reset={() => {}} />);
    expect(html).toContain("Something went wrong");
    expect(html).toContain("Try again");
    expect(html).toContain('href="/"');
    expect(html).toContain("abc123");
    expect(html).not.toContain("ORA-00942");
  });
});
