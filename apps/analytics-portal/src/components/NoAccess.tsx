import Link from "next/link";
import { visibleNav } from "@/lib/rowRules";
import type { RowRule } from "@/lib/rowRules";

type NavItem = { id: string; permission?: string | readonly string[] };

/**
 * Whether the page being opened is one the navigation would offer this person: the same rule
 * (permissions, row rules, the client's modules) applied to the page itself, so typing an
 * address reaches nothing the menu hides. A page outside the navigation is left to itself.
 */
export function pageOffered(
  nav: NavItem[],
  activeNav: string | undefined,
  user: { row_rules?: RowRule[] | null } | null,
  can: (permission: string) => boolean,
  modules?: Record<string, boolean>,
): boolean {
  if (!activeNav || !nav.some((i) => i.id === activeNav)) return true;
  return visibleNav(nav, user, can, modules).some((i) => i.id === activeNav);
}

export function NoAccess() {
  return (
    <section className="glass-panel mx-auto mt-10 max-w-xl p-8 text-center" data-testid="no-access">
      <h1 className="portal-heading text-xl font-bold">This page isn&apos;t available to your account</h1>
      <p className="mt-3 text-sm text-fg-muted">
        Your role or your organization&apos;s setup doesn&apos;t include it. If you need it, ask your administrator.
      </p>
      <Link href="/" className="btn-primary mt-5 inline-block text-sm">Back to Home</Link>
    </section>
  );
}
