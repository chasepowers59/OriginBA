import type { AuthStatus, AuthUser } from "@/lib/auth";

export type SessionState = { enabled: boolean; user: AuthUser | null; unreachable: boolean };

/** A failed or timed-out request, as opposed to the server answering with an error. */
function isUnreachable(err: unknown): boolean {
  return err instanceof TypeError
    || (err instanceof DOMException && (err.name === "TimeoutError" || err.name === "AbortError"));
}

/**
 * Who is signed in, settling in every case. An unreachable service is reported rather than
 * awaited: the bootstrap once awaited /auth/status outside any try, and the page stayed on
 * "Loading session…" for good whenever the API could not be reached. A token the server
 * rejects is cleared; one it could not be asked about is kept for the retry.
 */
export async function loadSession(d: {
  authDisabled: boolean;
  hasToken: boolean;
  fetchStatus: () => Promise<AuthStatus>;
  fetchUser: () => Promise<AuthUser>;
  clear: () => void;
}): Promise<SessionState> {
  let enabled = !d.authDisabled;
  if (enabled) {
    try {
      enabled = (await d.fetchStatus()).enabled;
    } catch {
      return { enabled: true, user: null, unreachable: true };
    }
  }
  if (enabled && !d.hasToken) return { enabled, user: null, unreachable: false };
  try {
    return { enabled, user: await d.fetchUser(), unreachable: false };
  } catch (err) {
    if (isUnreachable(err)) return { enabled, user: null, unreachable: true };
    if (enabled) d.clear();
    return { enabled, user: null, unreachable: false };
  }
}
