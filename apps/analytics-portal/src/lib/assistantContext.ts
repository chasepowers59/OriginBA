/**
 * Where the assistant is being asked from, and the conversation that follows the reader
 * between pages. A canvas page publishes its context; the assistant panel, wherever it
 * is mounted, reads it and sends it with the question.
 */
import type { Turn } from "./assistant";

export type PageContext = { canvas_id: string; label: string; period?: string; filters?: string[] };

let current: PageContext | null = null;
const listeners = new Set<() => void>();

export function setPageContext(context: PageContext | null): void {
  current = context;
  listeners.forEach((l) => l());
}

export function getPageContext(): PageContext | null {
  return current;
}

export function subscribePageContext(listener: () => void): () => void {
  listeners.add(listener);
  return () => void listeners.delete(listener);
}

export function contextLabel(c: PageContext): string {
  return c.period ? `${c.label} · ${c.period}` : c.label;
}

type Store = Pick<Storage, "getItem" | "setItem">;
const TURNS_KEY = "originba_assistant_turns";
// Kept to the last few exchanges: rows ride along in each answer.
const MAX_STORED_TURNS = 12;

function sessionStore(): Store | undefined {
  try {
    return typeof window === "undefined" ? undefined : window.sessionStorage;
  } catch {
    return undefined;
  }
}

export function loadTurns(store: Store | undefined = sessionStore()): Turn[] {
  try {
    const raw = store?.getItem(TURNS_KEY);
    const turns = raw ? JSON.parse(raw) : [];
    return Array.isArray(turns) ? turns : [];
  } catch {
    return [];
  }
}

export function saveTurns(turns: Turn[], store: Store | undefined = sessionStore()): void {
  try {
    store?.setItem(TURNS_KEY, JSON.stringify(turns.slice(-MAX_STORED_TURNS)));
  } catch {
    /* storage full or unavailable: the conversation just won't follow the reader */
  }
}
