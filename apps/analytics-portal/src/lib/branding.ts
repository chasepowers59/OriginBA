/** Origin is the platform brand; a client's own logo is shown beside it, never instead of it. */
const ORIGIN_MARKS = new Set(["/origin-mark.png", "/origin-logo.png", "/origin-logo-white.png", "/brand-icon.svg"]);

export function clientLogo(config: { brand?: { logo_src?: string | null } } | null | undefined): string | null {
  const src = config?.brand?.logo_src ?? "";
  return src && !ORIGIN_MARKS.has(src) ? src : null;
}
