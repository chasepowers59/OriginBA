/** Geometric workstream markers (no emoji). */
export const WORKSTREAM_ICONS: Record<string, string> = {
  finance: "◆",
  billing: "◇",
  meter_ops: "⬢",
  cashiering: "◉",
  debt: "◈",
  customer_ops: "◎",
  assets: "▤",
  field_ops: "▣",
  common: "⬡",
};

export function workstreamIcon(id: string): string {
  return WORKSTREAM_ICONS[id] ?? "•";
}
