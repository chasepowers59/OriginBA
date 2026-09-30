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
    expect(app).toContainEqual({ key: "Content-Security-Policy", value: "frame-ancestors 'none'" });
    expect(app).toContainEqual({ key: "X-Frame-Options", value: "DENY" });
    const embed = h.find((x) => x.source === "/embed/:path*")!.headers;
    expect(embed).toEqual([{ key: "Content-Security-Policy", value: "frame-ancestors 'self' https://intranet.utility.gov" }]);
  });

  it("with no sites configured, an embed is framed only by the portal itself", () => {
    expect(frameHeaders(undefined).find((x) => x.source === "/embed/:path*")!.headers[0].value).toBe("frame-ancestors 'self'");
  });
});
