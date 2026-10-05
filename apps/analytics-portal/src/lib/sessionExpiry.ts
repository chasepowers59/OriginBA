import { safeNext } from "./safeNext";

/** Whether an API answer means the session is over: any 401 except the sign-in call itself. */
export function endsSession(status: number, path: string): boolean {
  return status === 401 && !path.startsWith("/auth/login");
}

/** Where to send someone whose session ran out: sign-in, then back to the page they were on. */
export function expiredLoginUrl(pathname: string, search: string): string {
  return `/login?next=${encodeURIComponent(safeNext(`${pathname}${search}`))}&expired=1`;
}
