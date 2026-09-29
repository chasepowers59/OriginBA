"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { subscribeAsk } from "@/lib/assistantContext";
import { AssistantPanel } from "./AssistantPanel";
import { ORI } from "@/lib/ori";

/**
 * Ori on every page: a button that opens it beside the page. Home carries the
 * panel inline, so the button is not shown there. The conversation is the same one the
 * home panel shows (both read it from session storage).
 */
export function AssistantDrawer() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  // "Explain this number" on a card opens the drawer; the panel inside takes the question.
  useEffect(() => subscribeAsk(() => setOpen(true)), []);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  if (pathname === "/" || pathname.startsWith("/login")) return null;

  return (
    <div className="no-print">
      {open ? (
        <aside
          role="dialog"
          aria-label={ORI.ask}
          className="fixed inset-y-0 right-0 z-[60] w-full max-w-[480px] overflow-y-auto border-l border-edge-subtle bg-surface-solid p-3 shadow-2xl"
        >
          <div className="mb-2 flex justify-end">
            <button type="button" className="btn-ghost text-xs" onClick={() => setOpen(false)}>
              Close
            </button>
          </div>
          <AssistantPanel compact />
        </aside>
      ) : (
        <button
          type="button"
          onClick={() => setOpen(true)}
          aria-label={ORI.ask}
          className="btn-primary fixed bottom-4 right-4 z-[60] inline-flex h-12 w-12 items-center justify-center gap-2 rounded-full p-0 shadow-xl md:bottom-5 md:right-5 md:h-auto md:w-auto md:py-2.5 md:pl-2.5 md:pr-5"
        >
          <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-white">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/origin-mark.png" alt="" className="h-3.5 w-auto" />
          </span>
          <span className="hidden md:inline">{ORI.ask}</span>
        </button>
      )}
    </div>
  );
}
