"use client";

import { useState } from "react";
import { AdminAccessPanel } from "@/components/AdminAccessPanel";
import { settingsTabs, type SettingsTab } from "@/lib/settingsAccess";
import { ContentPackPanel } from "@/components/ContentPackPanel";
import { SystemHealthPanel } from "@/components/SystemHealthPanel";
import { DataSourceSettings } from "@/components/DataSourceSettings";
import { useAuth } from "@/components/AuthProvider";


export function SettingsTabs() {
  const { can } = useAuth();
  const tabs = settingsTabs(can);
  const [tab, setTab] = useState<SettingsTab>(tabs[0] ?? "connection");
  const shows = (t: SettingsTab) => tab === t && tabs.includes(t);

  return (
    <div className="space-y-6">
      {/* The page's title comes first, then the tabs: it used to sit inside the connection
          panel, under the tab bar, and the other tabs had none. */}
      <h1 className="text-2xl font-bold text-heading">Settings</h1>
      {tabs.length > 1 ? (
        <div className="glass-panel p-2">
          <div className="grid grid-cols-2 gap-1 md:grid-cols-4">
            {(
              [
                ["connection", "Database connection"],
                ["access", "Users & access"],
                ["packs", "Content packs"],
                ["health", "System health"],
              ] as const
            ).filter(([id]) => tabs.includes(id)).map(([id, label]) => (
              <button
                key={id}
                type="button"
                onClick={() => setTab(id)}
                className={`rounded-xl px-3 py-2.5 text-sm font-medium transition ${
 tab === id
 ? "tint-active portal-heading ring-1 ring-edge"
 : "portal-text-muted hover:bg-chip"
 }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      ) : null}

      {shows("connection") && can("data_source:manage") ? <DataSourceSettings /> : null}
      {tab === "connection" && !can("data_source:manage") ? (
        <div className="glass-panel p-6 text-sm portal-text-muted">
          Database connection settings are limited to administrators.
        </div>
      ) : null}
      {shows("access") ? <AdminAccessPanel /> : null}
      {shows("packs") ? <ContentPackPanel /> : null}
      {shows("health") ? <SystemHealthPanel /> : null}
    </div>
  );
}
