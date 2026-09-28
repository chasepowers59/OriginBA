/** Pages that need no sign-in, and who may put the portal in a frame. */

const PUBLIC = ["/login", "/change-password", "/embed"];

export function isPublicPath(pathname: string): boolean {
  return PUBLIC.some((p) => pathname === p || pathname.startsWith(`${p}/`));
}

/** Only an https origin (scheme and host, no path) may frame an embed. */
const ORIGIN = /^https:\/\/[a-z0-9.-]+(:\d+)?$/i;

/**
 * Response headers for next.config: nothing frames the app (clickjacking), and an embed may
 * be framed by the portal itself and the sites in EMBED_ALLOWED_ORIGINS (space-separated).
 */
export function frameHeaders(allowed: string | undefined) {
  const origins = (allowed ?? "").split(/\s+/).filter((o) => ORIGIN.test(o));
  return [
    { source: "/((?!embed/).*)", headers: [
      { key: "Content-Security-Policy", value: "frame-ancestors 'none'" },
      { key: "X-Frame-Options", value: "DENY" },
    ] },
    { source: "/embed/:path*", headers: [
      { key: "Content-Security-Policy", value: ["frame-ancestors 'self'", ...origins].join(" ") },
    ] },
  ];
}
