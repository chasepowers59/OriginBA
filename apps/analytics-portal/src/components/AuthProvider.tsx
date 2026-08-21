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

type AuthContextValue = {
  loading: boolean;
  enabled: boolean;
  user: AuthUser | null;
  can: (permission: string) => boolean;
  logout: () => void;
  refresh: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

const PUBLIC_PATHS = ["/login", "/change-password"];

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [loading, setLoading] = useState(true);
  const [enabled, setEnabled] = useState(authDisabled());
  const [user, setUser] = useState<AuthUser | null>(null);

  const refresh = useCallback(async () => {
    if (authDisabled()) {
      setEnabled(false);
      setUser({
        id: "dev-user",
        email: "dev@origin.local",
        display_name: "Development User",
        role: "admin",
        client_id: "demo",
        organization_id: "ellensburg",
        organization_name: "Ellensburg",
        is_active: true,
        must_change_password: false,
        workstreams: ["*"],
        permissions: [
          "portal:read",
          "report_library:read",
          "snapshots:read",
          "snapshots:query",
          "nlq:read",
          "saved_views:write",
          "dashboards:write",
          "explorer:builder",
          "users:manage",
          "groups:manage",
          "data_source:manage",
          "snapshots:raw_sql",
          "settings:manage",
        ],
        group_ids: [],
        group_names: [],
      });
      setLoading(false);
      return;
    }

    const status = await fetchAuthStatus();
    setEnabled(status.enabled);
    if (!status.enabled) {
      // Open-access mode still HAS a user -- the API answers /auth/me with its dev
      // context, an admin. Setting null here made the two modes diverge exactly where it
      // matters: anything keyed off a role silently disappeared, so the admin tenant
      // switcher was invisible in the only mode you can browse without signing in, and
      // looked like it had never been built.
      try {
        setUser(await fetchCurrentUser());
      } catch {
        setUser(null);
      }
      setLoading(false);
      return;
    }

    if (!getAccessToken()) {
      setUser(null);
      setLoading(false);
      return;
    }

    try {
      const me = await fetchCurrentUser();
      setUser(me);
    } catch {
      clearAuth();
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (loading || authDisabled() || !enabled) return;
    const isPublic = PUBLIC_PATHS.some((p) => pathname === p || pathname.startsWith(`${p}/`));
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
