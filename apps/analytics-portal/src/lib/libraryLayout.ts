/** How the report library opens: folded while browsing everything, open once the reader narrows it. */
export function packsStartOpen(s: { query: string; workstream: string | null; pack: string; packCount: number }): boolean {
  return Boolean(s.query.trim() || s.workstream || s.pack !== "all" || s.packCount <= 1);
}
