"use client";

import { ChevronDown } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { usePathname } from "next/navigation";
import { AssistantDrawer } from "./AssistantDrawer";
import { BrandMark } from "@/components/BrandMark";
import { useAuth } from "@/components/AuthProvider";
import { ThemeToggle } from "@/components/ThemeToggle";
import { roleLabel } from "@/lib/auth";
import OrgSwitcher from "@/components/OrgSwitcher";
import { useBrand, usePortalConfig } from "@/components/PortalThemeProvider";
import type { SnapshotSummary, WorkstreamGroup } from "@/lib/types";
import { isRestricted, visibleNav } from "@/lib/rowRules";
import { NoOrganization, needsOrganization } from "@/components/NoOrganization";
import { clientLogo } from "@/lib/branding";
import { fetchFreshness } from "@/lib/api";
import { freshnessNotice, type Freshness } from "@/lib/freshness";

// One clean top nav, one job per destination. "/" is the executive Home; Build is the
// single self-serve builder; Library is the one report catalog (and hosts the workstream
// browse tree); SQL is the one query surface. The ids are stable so each page's activeNav
// prop is unchanged even though labels/routes were rationalised.
const NAV = [
  { href: "/", label: "Home", id: "home" as const },
  { href: "/build", label: "Build", id: "build" as const },
  { href: "/dashboards", label: "Dashboards", id: "custom" as const },
  { href: "/reports", label: "Library", id: "reports" as const },
  { href: "/forecasts", label: "Forecasts", id: "forecasts" as const },
  { href: "/letters", label: "Letters", id: "letters" as const, permission: "letters:read" },
  { href: "/database", label: "SQL", id: "database" as const },
  { href: "/data-quality", label: "Data Quality", id: "dq" as const },
  // a client admin reaches Settings for their users alone (lib/settingsAccess.ts)
  { href: "/settings", label: "Settings", id: "settings" as const, permission: ["settings:manage", "users:manage"] as const },
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
  activeNav?: "home" | "reports" | "build" | "dashboard" | "custom" | "letters" | "database" | "dq" | "settings" | "forecasts";
  dbConfigured: boolean;
}) {
  const brand = useBrand();
  const portal = usePortalConfig();
  const { user, logout, can } = useAuth();
  // the active-organization cookie exists only in the browser: read after hydration
  // Every page says when the reporting data stopped refreshing (19 days unnoticed, 2026-09-29)
  const [freshness, setFreshness] = useState<Freshness | null>(null);
  useEffect(() => {
    if (!user) return;
    fetchFreshness().then(setFreshness).catch(() => setFreshness(null));
  }, [user]);
  const staleNotice = freshnessNotice(freshness);

  // Native <details> menus stay open until their summary is re-clicked; close
  // them on outside click and on navigation so they behave like real dropdowns.
  const headerRef = useRef<HTMLElement>(null);
  const pathname = usePathname();
  const closeMenus = () => {
    headerRef.current
      ?.querySelectorAll<HTMLDetailsElement>("details[open]")
      .forEach((d) => d.removeAttribute("open"));
  };
  useEffect(() => {
    const onPointerDown = (e: PointerEvent) => {
      headerRef.current
        ?.querySelectorAll<HTMLDetailsElement>("details[open]")
        .forEach((d) => {
          if (!d.contains(e.target as Node)) d.removeAttribute("open");
        });
    };
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, []);
  useEffect(closeMenus, [pathname]);

  return (
    <div className="mesh-bg flex min-h-screen flex-col">
      {/* Three-zone app bar: brand + org context | nav | compact controls. The meta
          that used to crowd the bar (workstream counts, role, org, sign out) lives in
          the user menu, so the bar itself stays one clean row at every width. */}
      <header ref={headerRef} className="portal-header no-print sticky top-0 z-50">
        <div className="mx-auto flex h-16 max-w-[1700px] items-center gap-2 px-4 sm:gap-4 sm:px-6 2xl:px-10">
          <div className="flex min-w-0 items-center gap-3">
            <Link href="/" aria-label="Origin home" className="group flex shrink-0 items-center">
              {/* the mark alone on phones leaves room for the organization chip */}
              <span className="sm:hidden"><BrandMark mark className="h-6 w-auto" /></span>
              <span className="hidden sm:inline-flex"><BrandMark className="h-7 w-auto" /></span>
            </Link>
            <span aria-hidden className="hidden h-6 w-px bg-edge-subtle sm:block" />
            {clientLogo(portal) ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={clientLogo(portal)!} alt={portal.organization_name ?? "Client"} className="hidden h-7 w-auto sm:block" />
            ) : null}
            {/* Below sm the switcher is in the account menu; the chip keeps whose data this is in view. */}
            {portal.organization_name ? (
              <span
                data-testid="org-chip"
                className="inline-flex min-w-0 max-w-[42vw] items-center truncate rounded-full border border-edge-subtle bg-chip px-2.5 py-1 text-xs font-medium text-fg sm:hidden"
              >
                <span className="truncate">{portal.organization_name}</span>
              </span>
            ) : null}
            <div className="hidden min-w-0 sm:block">
              <OrgSwitcher role={user?.role ?? ""} homeOrganizationId={user?.organization_id ?? null} />
              {user?.role !== "admin" ? (
                <p className="portal-text-muted truncate text-sm">{portal.organization_name}</p>
              ) : null}
            </div>
          </div>

          <nav className="hidden flex-1 items-center justify-center gap-0.5 md:flex">
            {visibleNav(NAV, user, can, portal?.modules).map((item) => {
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

          <div className="ml-auto flex shrink-0 items-center gap-1 sm:gap-2">
            {/* Mobile nav: below md the top nav is hidden, so this menu is the ONLY
                route to the app's surfaces on a phone. */}
            <details className="relative md:hidden">
              <summary
                className="flex h-9 w-9 cursor-pointer list-none items-center justify-center rounded-lg text-lg transition hover:bg-chip [&::-webkit-details-marker]:hidden"
                aria-label="Open navigation menu"
              >
                ☰
              </summary>
              <div className="glass-panel absolute right-0 top-full z-50 mt-2 w-56 p-2 shadow-xl">
                {visibleNav(NAV, user, can, portal?.modules).map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`block rounded-lg px-3 py-2 text-sm font-medium ${
 activeNav === item.id
 ? "bg-chip text-heading"
 : "text-fg-muted hover:bg-chip hover:text-heading"
 }`}
                  >
                    {item.label}
                  </Link>
                ))}
              </div>
            </details>
            {can("data_source:manage") ? (
              <Link
                href="/settings"
                className="hidden items-center gap-1.5 rounded-full px-2.5 py-1.5 text-xs font-medium text-fg-muted transition hover:bg-chip sm:flex"
                title={dbConfigured ? `${brand.connection_label} — database connection settings` : "Connect database"}
              >
                <span
                  className={`h-2 w-2 rounded-full ${dbConfigured ? "bg-ok dark:bg-ok" : "animate-pulse bg-warn dark:bg-warn"}`}
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
                  {/* primary-fg, not white: in dark mode --brand is a LIGHT blue meant
                      to sit ON dark, so white initials on it measured 2.29:1. The
                      palette already pairs each primary with its own foreground. */}
                  <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand text-xs font-bold text-primary-fg">
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
                  <ChevronDown aria-hidden className="portal-text-subtle h-3.5 w-3.5" />
                </summary>
                <div className="glass-panel absolute right-0 top-full z-50 mt-2 w-64 p-3 shadow-xl">
                  <p className="truncate text-sm font-semibold text-heading">{user.display_name}</p>
                  <p className="portal-text-muted mt-0.5 truncate text-xs">
                    {roleLabel(user.role)}
                    {user.organization_name ? ` · ${user.organization_name}` : ""}
                  </p>
                  {/* The bar only has room for the switcher at xl; without this an admin
                      on a narrower screen has no way to change tenant at all. */}
                  <OrgSwitcher
                    role={user.role}
                    homeOrganizationId={user.organization_id ?? null}
                    className="mt-2 flex min-w-0 items-center gap-1.5 xl:hidden"
                  />
                  <p className="portal-text-subtle mt-2 border-t border-edge-subtle pt-2 text-xs">
                    {workstreams.length} workstreams · {snapshots.length} data sets
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

      <div className="mx-auto w-full max-w-[1700px] flex-1 px-6 py-8 2xl:px-10">
        {staleNotice ? (
          <p role="status" data-testid="stale-data"
             className="mb-6 rounded-xl border border-warn bg-warn-bg px-4 py-3 text-sm text-warn">
            {staleNotice}
          </p>
        ) : null}
        {/* bottom room so the floating Ask Ori button never covers the page's last content */}
        <main className="min-w-0 animate-fade-in pb-24">
          {needsOrganization(user) ? <NoOrganization email={user!.email} /> : children}
        </main>
      </div>
      {user && !isRestricted(user) && !needsOrganization(user) ? <AssistantDrawer /> : null}

      <footer className="portal-footer no-print mt-8 py-6 text-center text-xs">
        {brand.name} · {brand.footer}
      </footer>
    </div>
  );
}
