"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { fetchDashboards } from "@/lib/api";
import { pinReportUrl } from "@/lib/pinReport";

type PinTarget = Parameters<typeof pinReportUrl>[0];

/**
 * "Pin to dashboard" with a destination: a new board, or appended to the first
 * free slot of an existing one (pins never replace tiles).
 */
export function PinMenu({
  target,
  className,
}: {
  target: Omit<PinTarget, "dashboardId">;
  className?: string;
}) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [boards, setBoards] = useState<{ id: string; title: string }[]>([]);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    fetchDashboards()
      .then((r) => setBoards(r.dashboards.map((d) => ({ id: d.id, title: d.title }))))
      .catch(() => setBoards([]));
    const onPointerDown = (e: PointerEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [open]);

  const go = (dashboardId?: string) => {
    setOpen(false);
    router.push(pinReportUrl({ ...target, dashboardId }));
  };

  return (
    <div ref={rootRef} className={`relative ${className ?? ""}`}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="btn-ghost block w-full text-center text-xs"
        aria-haspopup="menu"
        aria-expanded={open}
      >
        Pin to dashboard ▾
      </button>
      {open ? (
        <div
          role="menu"
          className="glass-panel absolute right-0 z-40 mt-1 w-56 p-1.5 shadow-xl"
        >
          <button
            type="button"
            role="menuitem"
            onClick={() => go(undefined)}
            className="block w-full rounded-lg px-3 py-2 text-left text-xs font-medium text-heading hover:bg-chip"
          >
            + New dashboard
          </button>
          {boards.length ? (
            <p className="px-3 pb-1 pt-2 text-[10px] font-semibold uppercase tracking-wider text-fg-muted">
              Add to existing
            </p>
          ) : null}
          {boards.map((b) => (
            <button
              key={b.id}
              type="button"
              role="menuitem"
              onClick={() => go(b.id)}
              className="block w-full truncate rounded-lg px-3 py-2 text-left text-xs text-fg hover:bg-chip"
            >
              {b.title}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
