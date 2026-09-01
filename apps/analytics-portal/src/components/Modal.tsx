"use client";

import { useEffect, type ReactNode } from "react";

/**
 * The portal's one dialog shell: overlay, click-outside and Escape to close, a
 * header with title/subtitle and a close button. Every modal (schedules, alerts,
 * notes) uses this so they behave identically.
 */
export function Modal({
  title,
  subtitle,
  onClose,
  children,
  size = "md",
}: {
  title: string;
  subtitle?: string;
  onClose: () => void;
  children: ReactNode;
  size?: "md" | "lg";
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-label={subtitle ? `${title}: ${subtitle}` : title}
      onClick={onClose}
    >
      <div
        className={`max-h-[85vh] w-full overflow-y-auto rounded-2xl border border-edge-subtle bg-surface p-5 shadow-2xl ${
          size === "lg" ? "max-w-lg" : "max-w-md"
        }`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 className="text-sm font-semibold text-heading">{title}</h2>
            {subtitle ? (
              <p className="mt-0.5 truncate text-xs text-fg-muted">
                {subtitle}
              </p>
            ) : null}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="rounded p-1 text-fg-muted hover:text-heading"
          >
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

/** Shown wherever a feature depends on SMTP the server may not have configured. */
export function SmtpNotice({ what }: { what: string }) {
  return (
    <p className="mt-3 rounded-lg border border-amber-400/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-700 dark:text-amber-300">
      Email delivery is not configured on the server yet — {what} save, but
      nothing sends until an administrator sets up SMTP.
    </p>
  );
}

/** The one error banner shape used inside dialogs. */
export function FormError({ children }: { children: string }) {
  return (
    <p
      role="alert"
      className="rounded-lg border border-red-400/40 bg-red-500/10 px-3 py-2 text-xs text-red-700 dark:text-red-300"
    >
      {children}
    </p>
  );
}
