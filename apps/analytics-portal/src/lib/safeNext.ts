const NOT_AFTER_SIGN_IN = ["/login", "/change-password"];

/**
 * Where to send someone after they sign in: the `next` path when it stays on this site, else
 * Home. A path starts with a single "/" (never "//" or "/\", which browsers read as another
 * host, nor its percent-encoded form), and never leads back to the sign-in pages.
 */
export function safeNext(next: string | null | undefined): string {
  if (!next || !next.startsWith("/") || next.startsWith("//") || next.startsWith("/\\")) return "/";
  let decoded = next;
  try {
    decoded = decodeURIComponent(next);
  } catch {
    return "/";
  }
  if (decoded.startsWith("//") || decoded.startsWith("/\\")) return "/";
  const path = next.split(/[?#]/, 1)[0];
  return NOT_AFTER_SIGN_IN.includes(path) ? "/" : next;
}
