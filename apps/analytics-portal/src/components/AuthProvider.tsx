"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { usePathname, useRouter } from "next/navigation";
import type { AuthUser } from "@/lib/auth";
import { authDisabled, getAccessToken, hasPermission } from "@/lib/auth";
import { fetchAuthStatus, fetchCurrentUser, logout as clearAuth } from "@/lib/authApi";
import { isPublicPath } from "@/lib/publicPaths";
import { loadSession } from "@/lib/sessionBootstrap";

type AuthContextValue = {
  loading: boolean;
  enabled: boolean;
  user: AuthUser | null;
  can: (permission: string) => boolean;
  logout: () => void;
  refresh: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [loading, setLoading] = useState(true);
  const [enabled, setEnabled] = useState(authDisabled());
  const [user, setUser] = useState<AuthUser | null>(null);
  const [unreachable, setUnreachable] = useState(false);

  const refresh = useCallback(async () => {
    setUnreachable(false);
    // The client flag only skips the login redirect; it must not invent an identity.
    // A fabricated user drifted from the API's dev context -- which builds itself from
    // `dev_organization_id()` and so cannot be tracked by a constant -- and the header
    // ended up naming one tenant over another tenant's data.
    // Open access (auth disabled) still HAS a user -- the API's dev admin -- so anything keyed
    // off a role (the tenant switcher) works in the mode you can browse without signing in.
    const session = await loadSession({
      authDisabled: authDisabled(),
      hasToken: Boolean(getAccessToken()),
      fetchStatus: fetchAuthStatus,
      fetchUser: fetchCurrentUser,
      clear: clearAuth,
    });
    setEnabled(session.enabled);
    setUser(session.user);
    setUnreachable(session.unreachable);
    setLoading(false);
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (loading || authDisabled() || !enabled) return;
    const isPublic = isPublicPath(pathname);
    if (!user && !isPublic) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
      return;
    }
    if (user?.must_change_password && pathname !== "/change-password") {
      router.replace("/change-password");
      return;
    }
    if (user && !user.must_change_password && pathname === "/login") {
      router.replace("/");
    }
    if (user && !user.must_change_password && pathname === "/change-password") {
      router.replace("/");
    }
  }, [loading, enabled, user, pathname, router]);

  const logout = useCallback(() => {
    clearAuth();
    setUser(null);
    router.replace("/login");
  }, [router]);

  const value = useMemo<AuthContextValue>(
    () => ({
      loading,
      enabled,
      user,
      can: (permission: string) => hasPermission(user, permission),
      logout,
      refresh,
    }),
    [loading, enabled, user, logout, refresh],
  );

  if (unreachable) {
    return (
      <div className="mesh-bg flex min-h-screen items-center justify-center">
        <div role="alert" className="glass-panel max-w-sm space-y-3 px-8 py-6 text-center">
          <p className="text-sm font-medium text-heading">The Origin BA service cannot be reached.</p>
          <p className="text-sm portal-text-muted">Check your connection, or try again in a minute.</p>
          <button type="button" className="btn-primary text-sm" onClick={() => { setLoading(true); void refresh(); }}>
            Try again
          </button>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="mesh-bg flex min-h-screen items-center justify-center">
        <div className="glass-panel px-8 py-6 text-sm portal-text-muted">Loading session…</div>
      </div>
    );
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}
