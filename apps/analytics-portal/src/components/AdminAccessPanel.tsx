"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { useAuth } from "@/components/AuthProvider";
import type { AccessGroup, AuthUser, PortalOrganization } from "@/lib/auth";
import {
  createAccessGroup,
  createPortalUser,
  deleteAccessGroup,
  listAccessGroups,
  listAuditEvents,
  listPortalOrganizations,
  listPortalUsers,
  type AuditEvent,
  updateAccessGroup,
  updatePortalUser,
} from "@/lib/authApi";

const WORKSTREAM_OPTIONS = [
  { id: "finance", label: "Finance" },
  { id: "billing", label: "Billing & Rates" },
  { id: "meter_ops", label: "Meter Operations" },
  { id: "cashiering", label: "Cashiering & Payments" },
  { id: "debt", label: "Collections & Debt" },
  { id: "customer_ops", label: "Customer Operations" },
  { id: "new_services", label: "New Services" },
  { id: "field_ops", label: "Field Operations" },
  { id: "common", label: "Operations & Shared Services" },
];

export function AdminAccessPanel() {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState<AuthUser[]>([]);
  const [groups, setGroups] = useState<AccessGroup[]>([]);
  const [organizations, setOrganizations] = useState<PortalOrganization[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [editingGroupId, setEditingGroupId] = useState<string | null>(null);
  const [groupDraft, setGroupDraft] = useState({
    name: "",
    description: "",
    workstreams: ["*"] as string[],
  });

  const [newUser, setNewUser] = useState({
    email: "",
    display_name: "",
    password: "",
    role: "user",
    organization_id: "",
    group_ids: [] as string[],
  });

  const [newGroup, setNewGroup] = useState({
    name: "",
    description: "",
    workstreams: ["*"] as string[],
  });

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const [u, g, audit, orgs] = await Promise.all([
        listPortalUsers(),
        listAccessGroups(),
        listAuditEvents(40),
        listPortalOrganizations(),
      ]);
      setUsers(u);
      setGroups(g);
      setAuditEvents(audit);
      setOrganizations(orgs);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load access data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  useEffect(() => {
    if (organizations.length && !newUser.organization_id) {
      setNewUser((s) => ({ ...s, organization_id: organizations[0].id }));
    }
  }, [organizations, newUser.organization_id]);

  async function handleCreateUser(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    try {
      await createPortalUser({
        ...newUser,
        organization_id: newUser.role === "admin" && !newUser.organization_id ? null : newUser.organization_id,
        is_active: true,
      });
      setNewUser({
        email: "",
        display_name: "",
        password: "",
        role: "user",
        organization_id: organizations[0]?.id ?? "",
        group_ids: [],
      });
      setMessage("User created");
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create user failed");
    }
  }

  async function runUserUpdate(userId: string, body: Parameters<typeof updatePortalUser>[1]) {
    setError(null);
    setMessage(null);
    try {
      await updatePortalUser(userId, body);
      setMessage("User updated");
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update user failed");
    }
  }

  function startEditGroup(group: AccessGroup) {
    setEditingGroupId(group.id);
    setGroupDraft({
      name: group.name,
      description: group.description,
      workstreams: group.workstreams.length ? group.workstreams : ["*"],
    });
  }

  async function saveGroupEdit(groupId: string) {
    setError(null);
    setMessage(null);
    try {
      await updateAccessGroup(groupId, groupDraft);
      setEditingGroupId(null);
      setMessage("Access group updated");
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update group failed");
    }
  }

  async function handleCreateGroup(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    try {
      await createAccessGroup(newGroup);
      setNewGroup({ name: "", description: "", workstreams: ["*"] });
      setMessage("Access group created");
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create group failed");
    }
  }

  if (loading) {
    return <div className="glass-panel p-6 text-sm portal-text-muted">Loading users and groups…</div>;
  }

  return (
    <div className="space-y-6">
      <div className="glass-panel p-5">
        <h2 className="text-lg font-semibold portal-heading">Users & roles</h2>
        <p className="mt-1 text-sm portal-text-muted">
          User = view and run reports. Editor = save views and dashboards. Admin = users, groups, and
          connection settings. Assign each user to one client environment (CityCorp, Odessa, etc.).
        </p>
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-edge-subtle text-left portal-text-subtle">
                <th className="px-3 py-2">Name</th>
                <th className="px-3 py-2">Email</th>
                <th className="px-3 py-2">Organization</th>
                <th className="px-3 py-2">Role</th>
                <th className="px-3 py-2">Groups</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Password</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id} className="border-b border-edge-subtle">
                  <td className="px-3 py-2 portal-heading">{user.display_name}</td>
                  <td className="px-3 py-2 portal-text-muted">{user.email}</td>
                  <td className="px-3 py-2">
                    <select
                      value={user.organization_id ?? ""}
                      onChange={(e) =>
                        void runUserUpdate(user.id, {
                          organization_id: e.target.value || null,
                        })
                      }
                      className="input-modern min-w-[9rem] py-1 text-xs"
                    >
                      <option value="">Platform admin</option>
                      {organizations.map((org) => (
                        <option key={org.id} value={org.id}>
                          {org.display_name}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="px-3 py-2">
                    <select
                      value={user.role}
                      disabled={user.id === currentUser?.id}
                      onChange={(e) => void runUserUpdate(user.id, { role: e.target.value })}
                      className="input-modern py-1 text-xs"
                      title={user.id === currentUser?.id ? "You cannot change your own role" : undefined}
                    >
                      <option value="user">User</option>
                      <option value="editor">Editor</option>
                      <option value="admin">Admin</option>
                    </select>
                  </td>
                  <td className="px-3 py-2">
                    <select
                      multiple
                      value={user.group_ids}
                      onChange={(e) =>
                        void runUserUpdate(user.id, {
                          group_ids: Array.from(e.target.selectedOptions).map((o) => o.value),
                        })
                      }
                      className="input-modern min-w-[10rem] py-1 text-xs"
                    >
                      {groups.map((g) => (
                        <option key={g.id} value={g.id}>
                          {g.name}
                        </option>
                      ))}
                    </select>
                    <p className="mt-1 text-xs portal-text-subtle">
                      {user.group_ids.length ? `${user.group_ids.length} selected` : "All workstreams"}
                    </p>
                  </td>
                  <td className="px-3 py-2">
                    <button
                      type="button"
                      className="chip text-xs"
                      disabled={user.id === currentUser?.id && user.is_active}
                      onClick={() => void runUserUpdate(user.id, { is_active: !user.is_active })}
                      title={user.id === currentUser?.id ? "You cannot deactivate yourself" : undefined}
                    >
                      {user.is_active ? "Active" : "Disabled"}
                    </button>
                  </td>
                  <td className="px-3 py-2">
                    <button
                      type="button"
                      className="btn-ghost text-xs"
                      onClick={() => {
                        const next = window.prompt(`Set a new temporary password for ${user.email}`);
                        if (next && next.length >= 8) {
                          void runUserUpdate(user.id, { password: next });
                        } else if (next) {
                          setError("Password must be at least 8 characters");
                        }
                      }}
                    >
                      Reset
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <form onSubmit={handleCreateUser} className="mt-6 grid gap-3 md:grid-cols-2">
          <input
            className="input-modern"
            placeholder="Display name"
            value={newUser.display_name}
            onChange={(e) => setNewUser((s) => ({ ...s, display_name: e.target.value }))}
            required
          />
          <input
            className="input-modern"
            type="email"
            placeholder="Email"
            value={newUser.email}
            onChange={(e) => setNewUser((s) => ({ ...s, email: e.target.value }))}
            required
          />
          <input
            className="input-modern"
            type="password"
            placeholder="Temporary password"
            value={newUser.password}
            onChange={(e) => setNewUser((s) => ({ ...s, password: e.target.value }))}
            required
          />
          <select
            className="input-modern"
            value={newUser.role}
            onChange={(e) => setNewUser((s) => ({ ...s, role: e.target.value }))}
          >
            <option value="user">User</option>
            <option value="editor">Editor</option>
            <option value="admin">Admin</option>
          </select>
          <select
            className="input-modern"
            value={newUser.organization_id}
            onChange={(e) => setNewUser((s) => ({ ...s, organization_id: e.target.value }))}
            required={newUser.role !== "admin"}
          >
            <option value="">{newUser.role === "admin" ? "Platform admin (all clients)" : "Select organization"}</option>
            {organizations.map((org) => (
              <option key={org.id} value={org.id}>
                {org.display_name}
              </option>
            ))}
          </select>
          <select
            multiple
            className="input-modern md:col-span-2"
            value={newUser.group_ids}
            onChange={(e) =>
              setNewUser((s) => ({
                ...s,
                group_ids: Array.from(e.target.selectedOptions).map((o) => o.value),
              }))
            }
          >
            {groups.map((g) => (
              <option key={g.id} value={g.id}>
                {g.name}
              </option>
            ))}
          </select>
          <button type="submit" className="btn-primary md:col-span-2">
            Add user
          </button>
        </form>
      </div>

      <div className="glass-panel p-5">
        <h2 className="text-lg font-semibold portal-heading">Access groups</h2>
        <p className="mt-1 text-sm portal-text-muted">
          Groups limit which workstreams a user can see in the sidebar and explorer.
        </p>
        <ul className="mt-4 space-y-3">
          {groups.map((group) => (
            <li key={group.id} className="rounded-xl border border-edge-subtle p-4">
              {editingGroupId === group.id ? (
                <div className="grid gap-3 md:grid-cols-2">
                  <input
                    className="input-modern"
                    value={groupDraft.name}
                    onChange={(e) => setGroupDraft((s) => ({ ...s, name: e.target.value }))}
                  />
                  <input
                    className="input-modern"
                    value={groupDraft.description}
                    onChange={(e) => setGroupDraft((s) => ({ ...s, description: e.target.value }))}
                  />
                  <select
                    multiple
                    className="input-modern md:col-span-2"
                    value={groupDraft.workstreams.includes("*") ? [] : groupDraft.workstreams}
                    onChange={(e) => {
                      const selected = Array.from(e.target.selectedOptions).map((o) => o.value);
                      setGroupDraft((s) => ({
                        ...s,
                        workstreams: selected.length ? selected : ["*"],
                      }));
                    }}
                  >
                    {WORKSTREAM_OPTIONS.map((ws) => (
                      <option key={ws.id} value={ws.id}>
                        {ws.label}
                      </option>
                    ))}
                  </select>
                  <div className="flex gap-2 md:col-span-2">
                    <button type="button" className="btn-primary text-xs" onClick={() => void saveGroupEdit(group.id)}>
                      Save
                    </button>
                    <button type="button" className="btn-ghost text-xs" onClick={() => setEditingGroupId(null)}>
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="font-medium portal-heading">{group.name}</p>
                    <p className="text-sm portal-text-muted">{group.description || "No description"}</p>
                    <p className="mt-1 text-xs portal-text-subtle">
                      Workstreams:{" "}
                      {group.workstreams.includes("*")
                        ? "All"
                        : group.workstreams
                            .map((id) => WORKSTREAM_OPTIONS.find((w) => w.id === id)?.label ?? id)
                            .join(", ")}
                      {" · "}
                      {group.member_count} members
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <button type="button" className="btn-ghost text-xs" onClick={() => startEditGroup(group)}>
                      Edit
                    </button>
                    <button
                      type="button"
                      className="btn-ghost text-xs"
                      onClick={() => void deleteAccessGroup(group.id).then(reload)}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              )}
            </li>
          ))}
        </ul>
        <form onSubmit={handleCreateGroup} className="mt-6 grid gap-3 md:grid-cols-2">
          <input
            className="input-modern"
            placeholder="Group name"
            value={newGroup.name}
            onChange={(e) => setNewGroup((s) => ({ ...s, name: e.target.value }))}
            required
          />
          <input
            className="input-modern"
            placeholder="Description"
            value={newGroup.description}
            onChange={(e) => setNewGroup((s) => ({ ...s, description: e.target.value }))}
          />
          <select
            multiple
            className="input-modern md:col-span-2"
            value={newGroup.workstreams.includes("*") ? [] : newGroup.workstreams}
            onChange={(e) => {
              const selected = Array.from(e.target.selectedOptions).map((o) => o.value);
              setNewGroup((s) => ({
                ...s,
                workstreams: selected.length ? selected : ["*"],
              }));
            }}
          >
            {WORKSTREAM_OPTIONS.map((ws) => (
              <option key={ws.id} value={ws.id}>
                {ws.label}
              </option>
            ))}
          </select>
          <p className="md:col-span-2 text-xs portal-text-subtle">
            Leave workstreams unselected for full access. Hold Cmd/Ctrl to select multiple.
          </p>
          <button type="submit" className="btn-primary md:col-span-2">
            Add access group
          </button>
        </form>
      </div>

      <div className="glass-panel p-5">
        <h2 className="text-lg font-semibold portal-heading">Recent admin activity</h2>
        <p className="mt-1 text-sm portal-text-muted">User, group, and password changes.</p>
        <ul className="mt-4 max-h-64 space-y-2 overflow-y-auto text-sm">
          {auditEvents.length ? (
            auditEvents.map((event) => (
              <li key={event.id} className="rounded-lg border border-edge-subtle px-3 py-2">
                <p className="portal-heading">
                  {event.action}
                  {event.detail ? ` — ${event.detail}` : ""}
                </p>
                <p className="text-xs portal-text-subtle">
                  {event.actor_email}
                  {event.created_at ? ` · ${new Date(event.created_at).toLocaleString()}` : ""}
                </p>
              </li>
            ))
          ) : (
            <li className="portal-text-muted">No audit events yet.</li>
          )}
        </ul>
      </div>

      {message ? <p className="text-sm text-ok">{message}</p> : null}
      {error ? <p className="text-sm text-over">{error}</p> : null}
    </div>
  );
}
