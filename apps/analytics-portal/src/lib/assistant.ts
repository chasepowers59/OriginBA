/**
 * The assistant conversation as the browser holds it: what the user asked, what came back,
 * and the model-facing thread the API hands back for a follow-up.
 */
import type { AssistantMessage, AssistantResponse } from "@/lib/types";

export type Turn =
  | { role: "user"; text: string }
  | { role: "assistant"; response: AssistantResponse }
  | { role: "error"; text: string };

/** The SQL workspace handoff: one key, the last query the reader chose to open. */
export const WORKSPACE_SQL_KEY = "portal.assistant.sql";

export function appendTurns(turns: Turn[], question: string, response: AssistantResponse): Turn[] {
  return [...turns, { role: "user", text: question }, { role: "assistant", response }];
}

/** The thread to send with the next question: the API's own, from the last answer. */
export function threadFor(turns: Turn[]): AssistantMessage[] {
  for (let i = turns.length - 1; i >= 0; i -= 1) {
    const t = turns[i];
    if (t.role === "assistant") return t.response.thread;
  }
  return [];
}

/** "3 steps · 2 queries · 1,240 tokens" -- the footer under an answer. */
export function summarise(r: AssistantResponse): string {
  const tokens = (r.usage?.input_tokens ?? 0) + (r.usage?.output_tokens ?? 0);
  const parts = [
    `${r.steps.length} step${r.steps.length === 1 ? "" : "s"}`,
    `${r.queries.length} ${r.queries.length === 1 ? "query" : "queries"}`,
  ];
  if (tokens) parts.push(`${tokens.toLocaleString()} tokens`);
  return parts.join(" · ");
}

/** A cell for the result table: numbers with separators, everything else as text. */
export function cell(v: unknown): string {
  if (v == null) return "";
  if (typeof v === "number") return Number.isInteger(v) ? v.toLocaleString() : v.toLocaleString(undefined, { maximumFractionDigits: 2 });
  return String(v);
}
