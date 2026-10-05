import { describe, expect, it } from "vitest";
import { frameHeaders, isPublicPath } from "./publicPaths";

describe("pages that need no sign-in", () => {
  it("login, password change and embeds are public; everything else is not", () => {
    for (const p of ["/login", "/login/x", "/change-password", "/embed/abc.def.ghi"]) expect(isPublicPath(p)).toBe(true);
    for (const p of ["/", "/embedded", "/explore/rpt_bill", "/settings"]) expect(isPublicPath(p)).toBe(false);
  });
});

describe("who may put the portal in a frame", () => {
  it("nobody frames the app; only the configured sites frame an embed", () => {
    const h = frameHeaders("https://intranet.utility.gov https://evil.test/path javascript:x");
    const app = h.find((x) => x.source === "/((?!embed/).*)")!.headers;
    expect(app.find((x) => x.key === "Content-Security-Policy")!.value.startsWith("frame-ancestors 'none';")).toBe(true);
    expect(app).toContainEqual({ key: "X-Frame-Options", value: "DENY" });
    const embed = h.find((x) => x.source === "/embed/:path*")!.headers;
    expect(embed.find((x) => x.key === "Content-Security-Policy")).toEqual(
      { key: "Content-Security-Policy", value: "frame-ancestors 'self' https://intranet.utility.gov" });
    expect(embed.some((x) => x.key === "X-Frame-Options")).toBe(false);   // an embed may be framed
  });

  it("with no sites configured, an embed is framed only by the portal itself", () => {
    expect(frameHeaders(undefined).find((x) => x.source === "/embed/:path*")!.headers[0].value).toBe("frame-ancestors 'self'");
  });
});

describe("every page carries the production security headers", () => {
  const all = (allowed?: string) => frameHeaders(allowed).flatMap((x) => x.headers.map((h) => [x.source, h.key, h.value]));
  it("nosniff, a referrer policy, a permissions policy and HSTS on every page, embeds included", () => {
    for (const source of ["/((?!embed/).*)", "/embed/:path*"]) {
      const keys = all().filter(([s]) => s === source).map(([, k]) => k);
      expect(keys).toEqual(expect.arrayContaining(["X-Content-Type-Options", "Referrer-Policy", "Permissions-Policy", "Strict-Transport-Security"]));
    }
  });
  it("the content policy also pins base-uri, object-src and form-action", () => {
    const csp = all().find(([s, k]) => s === "/((?!embed/).*)" && k === "Content-Security-Policy")![2];
    expect(csp).toContain("frame-ancestors 'none'");
    expect(csp).toContain("base-uri 'self'");
    expect(csp).toContain("object-src 'none'");
    expect(csp).toContain("form-action 'self'");
  });
});
