"use client";

import { useEffect, useState } from "react";
import { getActiveOrganization, setActiveOrganization } from "../lib/auth";
import type { PortalOrganization } from "../lib/auth";

/**
 * Tenant switcher for admins.
 *
 * Renders for nobody else, and that is a convenience rather than the control: the API
 * ignores the X-Organization-Id header unless the caller is an admin, so hiding this is
 * about not showing people a thing that would do nothing, not about keeping them out.
 *
 * A full reload on change, deliberately. Switching tenant changes which CATALOG is
 * served -- a Postgres tenant reads the dbt canvases, an Oracle tenant reads the CISADM
 * snapshots -- so every cached view, saved filter and pinned tile on the page belongs to
 * the previous tenant. Re-rendering in place would leave one tenant's field names sitting
 * over another tenant's data, which is the one thing a multi-tenant portal must never do.
 */
export default function OrgSwitcher({
  role,
  homeOrganizationId,
  className = "hidden min-w-0 shrink-0 items-center gap-1.5 xl:flex",
}: {
  role: string;
  homeOrganizationId?: string | null;
  /** The app bar has room for this only at xl; below that it rides in the user menu. */
  className?: string;
}) {
  const [orgs, setOrgs] = useState<PortalOrganization[]>([]);
  const [active, setActive] = useState<string>("");

  useEffect(() => {
    setActive(getActiveOrganization() ?? homeOrganizationId ?? "");
  }, [homeOrganizationId]);

  useEffect(() => {
    if (role !== "admin") return;
    let cancelled = false;
    (async () => {
      try {
        const { listPortalOrganizations } = await import("../lib/authApi");
        const list = await listPortalOrganizations();
        if (!cancelled) setOrgs(list);
      } catch {
        /* the switcher is optional chrome; a failure here must not break the header */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [role]);

  if (role !== "admin" || orgs.length === 0) return null;

  function choose(next: string) {
    setActive(next);
    setActiveOrganization(next === (homeOrganizationId ?? "") ? null : next);
    window.location.reload();
  }

  const viewingOther = Boolean(active) && active !== (homeOrganizationId ?? "");

  return (
    <label
      className={className}
      title={viewingOther ? "Admin: viewing another client's tenant" : "Admin: view another client"}
    >
      {/* Viewing someone else's tenant should never look like the default state:
          the select itself turns amber, plus a dot for colour-blind redundancy. */}
      {viewingOther && (
        <span aria-hidden className="h-2 w-2 shrink-0 rounded-full bg-warn" />
      )}
      <select
        value={active}
        onChange={(e) => choose(e.target.value)}
        aria-label="Client organization"
        // min-w-0 is load-bearing: a select defaults to min-width:auto, so it refuses to
        // shrink below its longest option and overflows the header's flex box instead of
        // truncating -- it sat on top of the Home and Explore nav links between lg and 2xl.
        className={`w-full min-w-[7.5rem] max-w-[180px] truncate rounded-lg border px-2 py-1.5 text-sm ${
 viewingOther
 ? "border-warn bg-warn-bg font-medium text-warn"
 : "border-edge-subtle bg-chip text-fg"
 }`}
      >
        {orgs.map((o) => (
          <option key={o.id} value={o.id}>
            {o.display_name}
          </option>
        ))}
      </select>
    </label>
  );
}
