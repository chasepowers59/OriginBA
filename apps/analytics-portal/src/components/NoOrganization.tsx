import type { AuthUser } from "@/lib/auth";

/** A reader who is not an administrator and has no client organization: nothing can load for them. */
export function needsOrganization(user: Pick<AuthUser, "role" | "organization_id"> | null | undefined): boolean {
  return Boolean(user && user.role !== "admin" && !user.organization_id);
}

/**
 * What such a reader sees instead of pages the server will refuse ("No organization assigned").
 * It names the account so they can quote it to whoever assigns organizations.
 */
export function NoOrganization({ email }: { email: string }) {
  return (
    <section className="glass-panel mx-auto mt-10 max-w-xl p-8 text-center" data-testid="no-organization">
      <h1 className="portal-heading text-xl font-bold">Your account isn&apos;t assigned to a client organization yet</h1>
      <p className="mt-3 text-sm text-fg-muted">
        Reports, dashboards and Ori read one organization&apos;s data, so there is nothing to show until an
        administrator assigns yours. Ask them to assign an organization to <strong>{email}</strong>, then sign in again.
      </p>
    </section>
  );
}
