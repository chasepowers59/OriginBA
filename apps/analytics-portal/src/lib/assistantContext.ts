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

// A question asked from elsewhere on the page ("Explain this number" on a card): held until
// a panel takes it. The drawer opens on the request; the panel that mounts takes it.
export type AskRequest = { question: string; context: PageContext | null };
let pendingAsk: AskRequest | null = null;
const askListeners = new Set<() => void>();

export function requestAsk(ask: AskRequest): void {
  pendingAsk = ask;
  askListeners.forEach((l) => l());
}

export function takeAsk(): AskRequest | null {
  const ask = pendingAsk;
  pendingAsk = null;
  return ask;
}

export function subscribeAsk(listener: () => void): () => void {
  askListeners.add(listener);
  return () => void askListeners.delete(listener);
}

/** The question behind "Explain this number": the figure, the card's own definition, the period. */
export function explainQuestion(card: { label: string; subtitle?: string | null }, value: string, period?: string | null): string {
  const definition = card.subtitle ? ` (defined as: ${card.subtitle})` : "";
  const when = period ? ` for ${period}` : "";
  return `Explain the "${card.label}" figure of ${value}${when}${definition}: how is it calculated, and what drives it? Reconcile to this figure.`;
}
