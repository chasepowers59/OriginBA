import type { QueryResponse } from "@/lib/types";

/**
 * Says out loud when the SERVER picked the date window, not the reader.
 *
 * A canvas query with no filters used to run unbounded on some canvases and silently
 * windowed on others — one read of one field causing opposite bugs. Every canvas with a
 * date is now windowed, which is the only way an aggregate over 6.08M rows stays
 * interactive (the row cap cannot help: FETCH FIRST applies after GROUP BY).
 *
 * That makes this component load-bearing rather than decorative. A default window that
 * nobody announces is a number narrower than the question asked, with nothing on screen
 * to explain the gap — which is exactly the bug this window once had. Renders
 * nothing when the reader set their own filters, because then the window is theirs.
 */
export function AppliedWindowNote({ result }: { result: QueryResponse | null }) {
  const applied = result?.applied_window;
  if (!applied) return null;
  return (
    <p
      className="text-xs"
      style={{ color: "var(--foreground-subtle)" }}
      data-testid="applied-window-note"
    >
      {applied.note}
    </p>
  );
}
