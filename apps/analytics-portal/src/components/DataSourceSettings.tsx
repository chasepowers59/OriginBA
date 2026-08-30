"use client";

import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/components/AuthProvider";
import {
  clearDataSourceConnection,
  fetchDataSourceStatus,
  getStoredSettingsToken,
  saveDataSourceConnection,
  storeSettingsToken,
  testDataSourceConnection,
} from "@/lib/api";
import type { DataSourceStatus } from "@/lib/types";

const SOURCE_LABELS: Record<DataSourceStatus["source"], string> = {
  portal_vault: "Portal vault (encrypted on server)",
  portal_memory: "Portal session (in-memory until API restart)",
  environment: "Server environment (.env)",
  none: "Not configured",
};

export function DataSourceSettings() {
  const { user: authUser } = useAuth();
  const [status, setStatus] = useState<DataSourceStatus | null>(null);
  const [dbUser, setDbUser] = useState("");
  const [password, setPassword] = useState("");
  const [dsn, setDsn] = useState("");
  const [libDir, setLibDir] = useState("");
  const [thickMode, setThickMode] = useState(false);
  const [adminToken, setAdminToken] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const s = await fetchDataSourceStatus();
    setStatus(s);
    setAdminToken(getStoredSettingsToken());
  }, []);

  useEffect(() => {
    void refresh().catch(() => setStatus(null));
  }, [refresh]);

  const payload = () => ({
    user: dbUser.trim(),
    password,
    dsn: dsn.trim(),
    oracle_client_lib_dir: libDir.trim() || undefined,
    thick_mode: thickMode,
  });

  const run = async (action: "test" | "save" | "clear") => {
    setLoading(true);
    setError(null);
    setMessage(null);
    storeSettingsToken(adminToken);
    try {
      if (action === "clear") {
        const res = await clearDataSourceConnection(adminToken);
        setStatus(res.status);
        setPassword("");
        setMessage("Portal connection cleared. Using .env if available.");
        return;
      }
      if (!dbUser.trim() || !password || !dsn.trim()) {
        setError("Username, password, and DSN are required.");
        return;
      }
      if (action === "test") {
        const res = await testDataSourceConnection(payload(), adminToken);
        if (res.ok) setMessage(res.message ?? "Connection successful.");
        else setError(res.error ?? "Connection failed.");
        return;
      }
      const res = await saveDataSourceConnection(payload(), adminToken);
      setStatus(res.status);
      setPassword("");
      setMessage("Connection saved on the server. Password is not stored in the browser.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sky-400">
          Data connection
        </p>
        <h1 className="mt-1 text-2xl font-bold text-heading">Settings</h1>
        <p className="mt-2 max-w-2xl text-sm text-fg-muted">
          Connect the analytics portal to your Oracle C2M database for{" "}
          <span className="text-heading">{authUser?.organization_name ?? "your assigned client"}</span>.
          Credentials are sent over HTTPS to the API only, encrypted at rest on the server, and never
          written to browser storage or git.
        </p>
      </div>

      {status ? (
        <div className="glass-panel p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-fg-muted">
            Current connection
          </p>
          <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-fg-muted">Source</dt>
              <dd className="text-heading">{SOURCE_LABELS[status.source]}</dd>
            </div>
            <div>
              <dt className="text-fg-muted">Status</dt>
              <dd className={status.configured ? "text-emerald-300" : "text-amber-300"}>
                {status.configured ? "Configured" : "Not connected"}
              </dd>
            </div>
            {status.user_masked ? (
              <div>
                <dt className="text-fg-muted">User</dt>
                <dd className="font-mono text-heading">{status.user_masked}</dd>
              </div>
            ) : null}
            {status.dsn_masked ? (
              <div>
                <dt className="text-fg-muted">DSN</dt>
                <dd className="font-mono text-heading">{status.dsn_masked}</dd>
              </div>
            ) : null}
          </dl>
        </div>
      ) : null}

      <form
        className="glass-panel space-y-4 p-6"
        onSubmit={(e) => {
          e.preventDefault();
          void run("save");
        }}
      >
        <p className="text-sm font-medium text-heading">Oracle connection</p>

        {status?.settings_token_required ? (
          <label className="block text-xs text-fg-muted">
            Admin settings token
            <input
              type="password"
              value={adminToken}
              onChange={(e) => setAdminToken(e.target.value)}
              className="input-modern mt-1"
              placeholder="PORTAL_SETTINGS_TOKEN from server .env"
              autoComplete="off"
            />
            <span className="mt-1 block text-[10px] text-fg-muted">
              Required to test or save. Stored in session storage only for this browser tab session.
            </span>
          </label>
        ) : null}

        <label className="block text-xs text-fg-muted">
          Database user
          <input
            type="text"
            value={dbUser}
            onChange={(e) => setDbUser(e.target.value)}
            className="input-modern mt-1"
            autoComplete="off"
            placeholder="CISADM read-only user"
          />
        </label>

        <label className="block text-xs text-fg-muted">
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="input-modern mt-1"
            autoComplete="new-password"
            placeholder="Not stored in the browser after save"
          />
        </label>

        <label className="block text-xs text-fg-muted">
          Connect string (DSN)
          <input
            type="text"
            value={dsn}
            onChange={(e) => setDsn(e.target.value)}
            className="input-modern mt-1 font-mono text-sm"
            autoComplete="off"
            placeholder="host.example.com:1521/ORCL"
          />
        </label>

        <label className="block text-xs text-fg-muted">
          Oracle Instant Client path (optional)
          <input
            type="text"
            value={libDir}
            onChange={(e) => setLibDir(e.target.value)}
            className="input-modern mt-1 font-mono text-sm"
            autoComplete="off"
            placeholder="/opt/oracle/instantclient_19_21"
          />
        </label>

        <label className="flex items-center gap-2 text-sm text-fg-muted">
          <input
            type="checkbox"
            checked={thickMode}
            onChange={(e) => setThickMode(e.target.checked)}
            className="rounded border-edge-subtle"
          />
          Use thick mode (required for some VPN / encryption setups)
        </label>

        <div className="flex flex-wrap gap-2 pt-2">
          <button
            type="button"
            className="btn-ghost"
            disabled={loading}
            onClick={() => void run("test")}
          >
            Test connection
          </button>
          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? "Saving…" : "Save connection"}
          </button>
          {status && (status.source === "portal_vault" || status.source === "portal_memory") ? (
            <button
              type="button"
              className="btn-ghost text-red-300"
              disabled={loading}
              onClick={() => void run("clear")}
            >
              Clear portal override
            </button>
          ) : null}
        </div>

        {message ? (
          <p className="rounded-lg border border-emerald-400/20 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-200">
            {message}
          </p>
        ) : null}
        {error ? (
          <p className="rounded-lg border border-red-400/20 bg-red-500/10 px-3 py-2 text-sm text-red-200">
            {error}
          </p>
        ) : null}
      </form>

      <div className="glass-panel p-4 text-xs text-fg-muted">
        <p className="font-medium text-fg-muted">Security notes</p>
        <ul className="mt-2 list-inside list-disc space-y-1">
          <li>Passwords are never returned by the API after save.</li>
          <li>Portal vault file is gitignored and encrypted with Fernet on the API server.</li>
          <li>Set <code className="text-fg-muted">PORTAL_SETTINGS_TOKEN</code> in production to gate changes.</li>
          <li>Prefer a read-only database account for analytics exploration.</li>
        </ul>
      </div>
    </div>
  );
}
