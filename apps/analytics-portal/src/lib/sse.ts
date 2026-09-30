/** Server-sent events from the assistant's streaming endpoint, parsed as chunks arrive. */

export type SseEvent = { type: string; data: Record<string, unknown> };

/** Complete events in `buffer`, and the unfinished tail to prepend to the next chunk. */
export function parseSse(buffer: string): { events: SseEvent[]; rest: string } {
  const blocks = buffer.split("\n\n");
  const rest = blocks.pop() ?? "";
  const events: SseEvent[] = [];
  for (const block of blocks) {
    let type = "message";
    let data = "";
    for (const line of block.split("\n")) {
      if (line.startsWith("event: ")) type = line.slice(7);
      else if (line.startsWith("data: ")) data += line.slice(6);
    }
    try {
      events.push({ type, data: data ? JSON.parse(data) : {} });
    } catch {
      /* a malformed event is skipped; the final answer or error still arrives */
    }
  }
  return { events, rest };
}

const STEP_WORDS: Record<string, string> = {
  list_canvases: "Finding the right report",
  describe_canvas: "Reading",
  search_knowledge: "Looking up the reference notes",
  verification_status: "Checking how far the figures can be trusted",
  run_sql: "Running:",
};

export function stepLabel(step: { tool?: unknown; detail?: unknown }): string {
  const words = STEP_WORDS[String(step.tool)] ?? String(step.tool);
  const detail = String(step.detail ?? "");
  if (step.tool === "describe_canvas" || step.tool === "run_sql") return detail ? `${words} ${detail}` : words.replace(/:$/, "");
  return words;
}
