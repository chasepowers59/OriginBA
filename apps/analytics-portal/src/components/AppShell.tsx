"use client";

import Link from "next/link";
import { Suspense, type ReactNode } from "react";
import { BrandMark } from "@/components/BrandMark";
import { useAuth } from "@/components/AuthProvider";
import { ThemeToggle } from "@/components/ThemeToggle";
import { roleLabel } from "@/lib/auth";
import OrgSwitcher from "@/components/OrgSwitcher";
import { WorkstreamSidebar, WorkstreamSidebarNav } from "@/components/WorkstreamExplorer";
import { useBrand, usePortalConfig } from "@/components/PortalThemeProvider";
import type { SnapshotSummary, WorkstreamGroup } from "@/lib/types";

const NAV = [
  { href: "/", label: "Home", id: "home" as const },
  { href: "/reports", label: "Reports", id: "reports" as const },
  { href: "/dashboard", label: "Dashboard", id: "dashboard" as const },
  { href: "/dashboard/custom", label: "My dashboards", id: "custom" as const },
  { href: "/database", label: "Database", id: "database" as const },
  { href: "/settings", label: "Settings", id: "settings" as const },
];

export function AppShell({
  children,
  snapshots,
  workstreams,
  activeId,
  activeNav,
  dbConfigured,
}: {
  children: ReactNode;
  snapshots: SnapshotSummary[];
  workstreams: WorkstreamGroup[];
  activeId?: string;
  activeNav?: "home" | "reports" | "dashboard" | "custom" | "database" | "settings";
  dbConfigured: boolean;
}) {
  const brand = useBrand();
  const portal = usePortalConfig();
  const { user, logout, can } = useAuth();

  return (
    <div className="mesh-bg min-h-screen">
      <header className="portal-header no-print sticky top-0 z-50">
        <div className="mx-auto flex max-w-[1400px] items-center justify-between px-6 py-4">
          <Link href="/" className="group flex items-center gap-4">
            <BrandMark />
            <div>
              <div className="flex flex-wrap items-baseline gap-2">
                <span className="portal-heading text-xl font-bold tracking-tight">{brand.name}</span>
                <span className="rounded-full bg-white/5 px-2 py-0.5 text-xs font-medium text-sky-600 ring-1 ring-white/10 dark:text-sky-300">
                  {brand.product}
                </span>
              </div>
              <p className="portal-text-muted text-sm">{portal.organization_name}</p>
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
                      ? "bg-white/10 portal-heading ring-1 ring-white/10"
                      : "portal-text-muted hover:bg-white/5 hover:text-slate-700 dark:hover:text-slate-200"
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

      <div className="mx-auto grid max-w-[1400px] gap-6 px-6 py-8 lg:grid-cols-[280px_1fr]">
        <aside className="no-print lg:sticky lg:top-24 lg:self-start">
          <div className="glass-panel p-4">
            <p className="mb-3 text-[11px] font-semibold uppercase tracking-widest text-sky-400/80">
              Workstreams
            </p>
            <Suspense
              fallback={
                <WorkstreamSidebar workstreams={workstreams} activeId={activeId} />
              }
            >
              <WorkstreamSidebarNav workstreams={workstreams} activeId={activeId} />
            </Suspense>
          </div>
        </aside>
        <main className="min-w-0 animate-fade-in">{children}</main>
      </div>

      <footer className="portal-footer no-print mt-8 py-6 text-center text-xs">
        {brand.name} · {brand.footer}
      </footer>
    </div>
  );
}
