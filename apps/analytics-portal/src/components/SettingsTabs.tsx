"use client";

import { useState } from "react";
import { AdminAccessPanel } from "@/components/AdminAccessPanel";
import { DataSourceSettings } from "@/components/DataSourceSettings";
import { useAuth } from "@/components/AuthProvider";

type Tab = "connection" | "access";

export function SettingsTabs() {
  const { can } = useAuth();
  const isAdmin = can("settings:manage");
  const [tab, setTab] = useState<Tab>(isAdmin ? "connection" : "connection");

  return (
    <div className="space-y-6">
      {isAdmin ? (
        <div className="glass-panel p-2">
          <div className="grid grid-cols-2 gap-1">
            {(
              [
                ["connection", "Database connection"],
                ["access", "Users & access"],
              ] as const
            ).map(([id, label]) => (
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

      {tab === "connection" && can("data_source:manage") ? <DataSourceSettings /> : null}
      {tab === "connection" && !can("data_source:manage") ? (
        <div className="glass-panel p-6 text-sm portal-text-muted">
          Database connection settings are limited to administrators.
        </div>
      ) : null}
      {tab === "access" && isAdmin ? <AdminAccessPanel /> : null}
    </div>
  );
}
