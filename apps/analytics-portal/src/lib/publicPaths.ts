/** Pages that need no sign-in, and who may put the portal in a frame. */

const PUBLIC = ["/login", "/change-password", "/embed"];

export function isPublicPath(pathname: string): boolean {
  return PUBLIC.some((p) => pathname === p || pathname.startsWith(`${p}/`));
}

/** Only an https origin (scheme and host, no path) may frame an embed. */
const ORIGIN = /^https:\/\/[a-z0-9.-]+(:\d+)?$/i;

/** On every page, embeds included (production-readiness audit, 2026-10-05). */
const COMMON = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=(), usb=()" },
  { key: "Strict-Transport-Security", value: "max-age=31536000; includeSubDomains" },
];

/**
 * Response headers for next.config: nothing frames the app (clickjacking), and an embed may
 * be framed by the portal itself and the sites in EMBED_ALLOWED_ORIGINS (space-separated).
 * The app's content policy also pins base-uri, object-src and form-action, which need no
 * script nonces; a full script-src policy is the remaining step.
 */
export function frameHeaders(allowed: string | undefined) {
  const origins = (allowed ?? "").split(/\s+/).filter((o) => ORIGIN.test(o));
  return [
    { source: "/((?!embed/).*)", headers: [
      { key: "Content-Security-Policy", value: "frame-ancestors 'none'; base-uri 'self'; object-src 'none'; form-action 'self'" },
      { key: "X-Frame-Options", value: "DENY" },
      ...COMMON,
    ] },
    { source: "/embed/:path*", headers: [
      { key: "Content-Security-Policy", value: ["frame-ancestors 'self'", ...origins].join(" ") },
      ...COMMON,
    ] },
  ];
}
