"use client";

import { exportDashboardCsv, printDashboardPack } from "@/lib/exportDashboard";

type PresentationToolbarProps = {
  title: string;
  exportSections?: { name: string; headers: string[]; rows: Record<string, unknown>[] }[];
  targetId?: string;
};

export function PresentationToolbar({
  title,
  exportSections = [],
  targetId = "dashboard-export-root",
}: PresentationToolbarProps) {
  const enterPresentation = () => {
    document.documentElement.classList.add("presentation-mode");
    void document.documentElement.requestFullscreen?.().catch(() => {});
  };

  const exitPresentation = () => {
    document.documentElement.classList.remove("presentation-mode");
    if (document.fullscreenElement) {
      void document.exitFullscreen?.().catch(() => {});
    }
  };

  return (
    <div className="no-print flex flex-wrap items-center gap-2">
      <button type="button" onClick={enterPresentation} className="btn-primary">
        Present
      </button>
      <button type="button" onClick={() => printDashboardPack(title, targetId)} className="btn-ghost">
        Export PDF pack
      </button>
      {exportSections.length ? (
        <button
          type="button"
          onClick={() => exportDashboardCsv(title, exportSections)}
          className="btn-ghost"
        >
          Export Excel pack
        </button>
      ) : null}
      <button type="button" onClick={exitPresentation} className="btn-ghost text-xs text-fg-muted">
        Exit present
      </button>
    </div>
  );
}
