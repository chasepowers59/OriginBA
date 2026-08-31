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
      <header className="portal-header no-print sticky top-0 z-50">
        <div className="mx-auto flex max-w-[1400px] items-center justify-between px-6 py-4">
          <Link href="/" className="group flex items-center gap-3">
            <BrandMark className="h-8 w-auto" />
            <div className="hidden border-l border-edge-subtle pl-3 sm:block">
              <span className="rounded-full bg-chip px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wider text-brand ring-1 ring-edge-subtle">
                {brand.product}
              </span>
              <p className="portal-text-muted mt-1 text-xs">{portal.organization_name}</p>
            </div>
          </Link>
          <div className="flex items-center gap-4">
            <OrgSwitcher role={user?.role ?? ""} homeOrganizationId={user?.organization_id ?? null} />
          </div>
          <nav className="hidden items-center gap-1 md:flex">
            {NAV.filter((item) => item.id !== "settings" || can("settings:manage")).map((item) => {
              const active = activeNav === item.id || (!activeNav && item.id === "home");
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`rounded-xl px-4 py-2 text-sm font-medium transition ${
                    active
                      ? "bg-chip portal-heading ring-1 ring-edge-subtle"
                      : "portal-text-muted hover:bg-chip hover:text-slate-700 dark:hover:text-heading"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
          <div className="flex items-center gap-3">
            <span className="portal-text-subtle hidden text-xs lg:inline">
              {workstreams.length} workstreams · {snapshots.length} domains
            </span>
            <ThemeToggle />
            {user ? (
              <div className="hidden items-center gap-2 md:flex">
                <span className="portal-text-muted text-xs">
                  {user.display_name}
                  {user.organization_name ? ` · ${user.organization_name}` : ""} · {roleLabel(user.role)}
                </span>
                <button type="button" onClick={logout} className="btn-ghost px-2.5 py-1.5 text-xs">
                  Sign out
                </button>
              </div>
            ) : null}
            {can("data_source:manage") ? (
              <Link
                href="/settings"
                className={`flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-medium ring-1 transition hover:ring-white/20 ${
                  dbConfigured
                    ? "bg-emerald-500/10 text-emerald-700 ring-emerald-400/30 dark:text-emerald-300 dark:ring-emerald-400/20"
                    : "bg-amber-500/10 text-amber-800 ring-amber-400/30 dark:text-amber-300 dark:ring-amber-400/20"
                }`}
                title="Database connection settings"
              >
                <span
                  className={`h-2 w-2 rounded-full ${dbConfigured ? "animate-pulse bg-emerald-500 dark:bg-emerald-400" : "bg-amber-500 dark:bg-amber-400"}`}
                />
                {dbConfigured ? brand.connection_label : "Connect database"}
              </Link>
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
