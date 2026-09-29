"use client";

import { useEffect, useRef, useState } from "react";

/**
 * A toolbar popup's panel. Below sm it spans the toolbar (whose wrapper is `relative`)
 * rather than its button: anchored to a button that wrapped to the left edge of a 320 px
 * screen, a fixed-width panel opened off the page.
 */
export const POPOVER_PANEL =
  "glass-panel absolute inset-x-0 z-40 mt-1 p-1.5 shadow-xl sm:inset-x-auto sm:right-0";

/** The item a menu key moves focus to, or null for a key the menu leaves to the browser. */
export function menuFocusIndex(key: string, current: number, count: number): number | null {
  if (!count) return null;
  if (key === "Home") return 0;
  if (key === "End") return count - 1;
  if (key === "ArrowDown") return current < 0 ? 0 : (current + 1) % count;
  if (key === "ArrowUp") return current < 0 ? count - 1 : (current - 1 + count) % count;
  return null;
}

/** Open state for a button's popup: a pointer outside or Escape closes it, and Escape returns focus to the button. */
export function usePopover() {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (e: PointerEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      setOpen(false);
      triggerRef.current?.focus();
    };
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  return { open, setOpen, rootRef, triggerRef };
}
