"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { subscribeAsk } from "@/lib/assistantContext";
import { AssistantPanel } from "./AssistantPanel";

/**
 * The assistant on every page: a button that opens it beside the page. Home carries the
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
          aria-label="Ask the assistant"
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
          className="btn-primary fixed bottom-5 right-5 z-[60] rounded-full px-5 py-3 shadow-xl"
        >
          Ask the assistant
        </button>
      )}
    </div>
  );
}
