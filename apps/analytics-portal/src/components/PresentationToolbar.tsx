"use client";

import { useCallback, useEffect, useState } from "react";
import { exportDashboardXlsx, printDashboardPack } from "@/lib/exportDashboard";
import {
  enterPresentation,
  exitPresentation,
  isPresenting,
  toolbarControls,
} from "@/lib/presentationMode";

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
  const [presenting, setPresenting] = useState(false);

  const stop = useCallback(() => {
    exitPresentation(document.documentElement);
    setPresenting(false);
    if (document.fullscreenElement) {
      void document.exitFullscreen?.().catch(() => {});
    }
  }, []);

  const start = () => {
    enterPresentation(document.documentElement);
    setPresenting(true);
    void document.documentElement.requestFullscreen?.().catch(() => {});
  };

  useEffect(() => {
    // Escape leaves fullscreen without telling React, and used to leave the class
    // behind — the app then stayed stripped down until a reload. Watch both, because
    // if the fullscreen request was denied there is no fullscreenchange to hear.
    const onFullscreenChange = () => {
      if (!document.fullscreenElement && isPresenting(document.documentElement)) stop();
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && isPresenting(document.documentElement)) stop();
    };
    document.addEventListener("fullscreenchange", onFullscreenChange);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("fullscreenchange", onFullscreenChange);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [stop]);

  // Never strand a session in presentation mode because a component unmounted.
  useEffect(() => () => exitPresentation(document.documentElement), []);

  const controls = toolbarControls(presenting);

  if (controls.showExit) {
    // Deliberately NOT inside `.no-print`: presentation mode hides that class, which
    // is how the exit button hid itself. `print:hidden` keeps it out of the PDF pack.
    return (
      <div className="flex items-center gap-2 print:hidden">
        <button type="button" onClick={stop} className="btn-ghost text-xs">
          Exit present
        </button>
        <span className="text-xs text-fg-muted">or press Esc</span>
      </div>
    );
  }

  return (
    <div className="no-print flex flex-wrap items-center gap-2">
      <button type="button" onClick={start} className="btn-primary">
        Present
      </button>
      {controls.showExports ? (
        <button
          type="button"
          onClick={() => printDashboardPack(title, targetId)}
          className="btn-ghost"
        >
          Export PDF pack
        </button>
      ) : null}
      {controls.showExports && exportSections.length ? (
        <button
          type="button"
          onClick={() => exportDashboardXlsx(title, exportSections)}
          className="btn-ghost"
        >
          Export Excel pack
        </button>
      ) : null}
    </div>
  );
}
