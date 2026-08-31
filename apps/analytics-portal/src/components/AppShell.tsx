"use client";

import Link from "next/link";
import { type ReactNode } from "react";
import { BrandMark } from "@/components/BrandMark";
import { useAuth } from "@/components/AuthProvider";
import { ThemeToggle } from "@/components/ThemeToggle";
import { roleLabel } from "@/lib/auth";
import OrgSwitcher from "@/components/OrgSwitcher";
import { useBrand, usePortalConfig } from "@/components/PortalThemeProvider";
import type { SnapshotSummary, WorkstreamGroup } from "@/lib/types";

// One clean top nav, one job per destination. "/" is the executive Home; Explore is the
// single self-serve builder; Library is the one report catalog (and hosts the workstream
// browse tree); SQL is the one query surface. The ids are stable so each page's activeNav
// prop is unchanged even though labels/routes were rationalised.
const NAV = [
  { href: "/", label: "Home", id: "home" as const },
  { href: "/build", label: "Explore", id: "build" as const },
  { href: "/dashboards", label: "Dashboards", id: "custom" as const },
  { href: "/reports", label: "Library", id: "reports" as const },
  { href: "/database", label: "SQL", id: "database" as const },
  { href: "/data-quality", label: "Data Quality", id: "dq" as const },
  { href: "/settings", label: "Settings", id: "settings" as const },
];

export function AppShell({
  children,
  snapshots,
  workstreams,
  activeNav,
  dbConfigured,
}: {
  children: ReactNode;
  snapshots: SnapshotSummary[];
  workstreams: WorkstreamGroup[];
  activeId?: string;
  activeNav?: "home" | "reports" | "build" | "dashboard" | "custom" | "database" | "dq" | "settings";
  dbConfigured: boolean;
}) {
  const brand = useBrand();
  const portal = usePortalConfig();
  const { user, logout, can } = useAuth();

  return (
    <div className="mesh-bg min-h-screen">
      {/* Three-zone app bar: brand + org context | nav | compact controls. The meta
          that used to crowd the bar (workstream counts, role, org, sign out) lives in
          the user menu, so the bar itself stays one clean row at every width. */}
      <header className="portal-header no-print sticky top-0 z-50">
        <div className="mx-auto flex h-16 max-w-[1400px] items-center gap-4 px-6">
          <div className="flex min-w-0 items-center gap-3">
            <Link href="/" className="group flex shrink-0 items-center">
              <BrandMark className="h-7 w-auto" />
            </Link>
            <span aria-hidden className="hidden h-6 w-px bg-edge-subtle sm:block" />
            <div className="hidden min-w-0 sm:block">
              <OrgSwitcher role={user?.role ?? ""} homeOrganizationId={user?.organization_id ?? null} />
              {user?.role !== "admin" ? (
                <p className="portal-text-muted truncate text-sm">{portal.organization_name}</p>
              ) : null}
            </div>
          </div>

          <nav className="hidden flex-1 items-center justify-center gap-0.5 md:flex">
            {NAV.filter((item) => item.id !== "settings" || can("settings:manage")).map((item) => {
              const active = activeNav === item.id || (!activeNav && item.id === "home");
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium transition ${
                    active
                      ? "bg-chip portal-heading ring-1 ring-edge-subtle"
                      : "portal-text-muted hover:bg-chip hover:text-heading"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>

          <div className="ml-auto flex shrink-0 items-center gap-2">
            {can("data_source:manage") ? (
              <Link
                href="/settings"
                className="flex items-center gap-1.5 rounded-full px-2.5 py-1.5 text-xs font-medium text-fg-muted transition hover:bg-chip"
                title={dbConfigured ? `${brand.connection_label} — database connection settings` : "Connect database"}
              >
                <span
                  className={`h-2 w-2 rounded-full ${dbConfigured ? "bg-emerald-500 dark:bg-emerald-400" : "animate-pulse bg-amber-500 dark:bg-amber-400"}`}
                />
                <span className="hidden xl:inline">
                  {dbConfigured ? brand.connection_label : "Connect"}
                </span>
              </Link>
            ) : null}
            <ThemeToggle />
            {user ? (
              <details className="group/menu relative">
                <summary className="flex cursor-pointer list-none items-center gap-2 rounded-lg px-2 py-1.5 transition hover:bg-chip [&::-webkit-details-marker]:hidden">
                  <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand text-xs font-bold text-white">
                    {user.display_name
                      .split(/\s+/)
                      .map((w) => w.charAt(0))
                      .join("")
                      .slice(0, 2)
                      .toUpperCase()}
                  </span>
                  <span className="portal-text-muted hidden max-w-[120px] truncate text-sm lg:block">
                    {user.display_name}
                  </span>
                  <span aria-hidden className="portal-text-subtle text-[10px]">▾</span>
                </summary>
                <div className="glass-panel absolute right-0 top-full z-50 mt-2 w-64 p-3 shadow-xl">
                  <p className="truncate text-sm font-semibold text-heading">{user.display_name}</p>
                  <p className="portal-text-muted mt-0.5 truncate text-xs">
                    {roleLabel(user.role)}
                    {user.organization_name ? ` · ${user.organization_name}` : ""}
                  </p>
                  <p className="portal-text-subtle mt-2 border-t border-edge-subtle pt-2 text-xs">
                    {workstreams.length} workstreams · {snapshots.length} reporting canvases
                  </p>
                  <button type="button" onClick={logout} className="btn-ghost mt-3 w-full text-xs">
                    Sign out
                  </button>
                </div>
              </details>
            ) : null}
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-[1400px] px-6 py-8">
        <main className="min-w-0 animate-fade-in">{children}</main>
      </div>

      <footer className="portal-footer no-print mt-8 py-6 text-center text-xs">
        {brand.name} · {brand.footer}
      </footer>
    </div>
  );
}
