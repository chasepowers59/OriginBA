import { isPublicPath } from "./publicPaths";
import { safeNext } from "./safeNext";

/** Whether an API answer means the session is over: a 401 on anything but the sign-in call,
 *  when there IS a session, on a page that needs one. A signed-out visitor of the sign-in
 *  page gets 401s from its own calls, and ending a session that did not exist redirected the
 *  page to itself and lost ?next= (found live 2026-10-05). */
export function endsSession(status: number, path: string, ctx: { hasSession: boolean; page: string }): boolean {
  return status === 401 && !path.startsWith("/auth/login") && ctx.hasSession && !isPublicPath(ctx.page);
}

/** Where to send someone whose session ran out: sign-in, then back to the page they were on. */
export function expiredLoginUrl(pathname: string, search: string): string {
  return `/login?next=${encodeURIComponent(safeNext(`${pathname}${search}`))}&expired=1`;
}
