import { cookies } from "next/headers";

/**
 * The SSR session cookie, set server-side so JavaScript can never read it.
 *
 * Next's server components forward `Authorization` to the API from this cookie
 * (lib/api.ts). It used to be written with `document.cookie` — readable by any
 * script on the page, with a 48-hour life regardless of when the token expired —
 * so a single XSS lifted a usable token (audit H6). The API lives on another
 * origin and cannot set a cookie here, so this same-origin route does it.
 *
 * The token still reaches the browser (the SPA sends it on its own fetches from
 * sessionStorage); what changes is that the persistent copy is no longer
 * scriptable and no longer outlives the token.
 */
const COOKIE = "portal_access_token";
// Never longer than a day, whatever the caller claims, and the caller normally
// passes the token's own remaining life.
const MAX_AGE_CEILING = 24 * 3600;

export async function POST(request: Request): Promise<Response> {
  let payload: { token?: unknown; maxAge?: unknown };
  try {
    payload = await request.json();
  } catch {
    return new Response(null, { status: 400 });
  }

  const token = typeof payload.token === "string" ? payload.token : "";
  if (!token) return new Response(null, { status: 400 });

  const requested = Number(payload.maxAge);
  const maxAge = Math.min(
    Number.isFinite(requested) && requested > 0 ? requested : MAX_AGE_CEILING,
    MAX_AGE_CEILING,
  );

  const jar = await cookies();
  jar.set(COOKIE, token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge,
  });
  return new Response(null, { status: 204 });
}

export async function DELETE(): Promise<Response> {
  const jar = await cookies();
  jar.delete(COOKIE);
  return new Response(null, { status: 204 });
}
