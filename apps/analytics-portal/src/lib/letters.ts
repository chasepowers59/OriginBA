/**
 * Collections letters as the review page sees them (the API: api/letters/routes.py). Ported from
 * the letter-print app's review UI (originba-letterprint web/src/lib/letters.ts).
 */
import { ApiError } from "./apiErrors";

/** The API serializes Decimal as text ("132.69"); every helper here takes the wire shape. */
export type Money = string | number | null;

export type LetterSummary = {
  letter_id: string;
  kind: string;
  kind_label: string;
  template_code: string;
  contact_type: string;
  letter_date: string;
  account_id: string;
  /** The customer's name: searched, but shown only in the detail pane. */
  recipient: string;
  amount: Money;
  process_type: string;
  process_id: string;
  next_action_on: string | null;
  printed: boolean;
  copies: number;
};

export type LetterList = { organization_id: string; from: string; to: string; count: number; letters: LetterSummary[] };

export type LetterService = { sa_id: string; service_type: string; premise_address: string; amount: Money };

export type LetterDetail = {
  organization_id: string;
  letter: LetterSummary;
  recipient: { customer_name: string; person_id: string; address_lines: string[] };
  composed: {
    subject: string;
    paragraphs: string[];
    callout: string;
    glance_label: string;
    glance_amount: Money;
  };
  process: {
    process_type: string;
    process_id: string;
    template_code: string;
    arrears_amount: Money;
    arrears_as_of: string | null;
    next_action_on: string | null;
    next_action_type: string;
    cut_scheduled_on: string | null;
    cut_completed_on: string | null;
    services: LetterService[];
  } | null;
  returned_payment: {
    adjustment_id: string;
    fee_amount: Money;
    payment_date: string | null;
    payment_amount: Money;
    tender_type: string;
  } | null;
  late_fee: {
    adjustment_id: string;
    amount: Money;
    charged_on: string;
    service_type: string;
    premise_address: string;
  } | null;
  account_balance: Money;
  contact_id: string | null;
  body: string;
  created_at: string;
  printed_at: string | null;
};

/** The rendered letter and the face it was set in; `fontNote` says when the approved one was missing. */
export type LetterPdf = { blob: Blob; font: string; fontNote: string | null };

export type Printed = "all" | "printed" | "not_printed";
export type Filters = { search: string; kinds: string[]; printed: Printed };
export const NO_FILTERS: Filters = { search: "", kinds: [], printed: "all" };

export type Facet = { value: string; label: string; count: number };

/** A missing amount stays missing: Number(null) and Number("") are both 0. */
function amountValue(value: Money | undefined): number | null {
  if (value == null || value === "") return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function matchesSearch(l: LetterSummary, term: string): boolean {
  const t = term.trim().toLowerCase();
  if (!t) return true;
  return [l.account_id, l.recipient, l.letter_id, l.kind_label, l.contact_type, l.process_id]
    .some((f) => (f ?? "").toLowerCase().includes(t));
}

export function applyFilters(letters: LetterSummary[], f: Filters): LetterSummary[] {
  return letters.filter(
    (l) =>
      matchesSearch(l, f.search) &&
      (f.kinds.length === 0 || f.kinds.includes(l.kind)) &&
      (f.printed === "all" || (f.printed === "printed") === l.printed),
  );
}

/**
 * Letter types with counts, computed with the type selection itself REMOVED so the other types
 * stay clickable. A chosen type the other filters have emptied stays listed at 0: otherwise a
 * filter still narrowing the table would have no control left on screen to remove it.
 */
export function kindFacets(letters: LetterSummary[], f: Filters): Facet[] {
  const counts = new Map<string, Facet>();
  for (const l of letters) {
    if (f.kinds.includes(l.kind) && !counts.has(l.kind)) counts.set(l.kind, { value: l.kind, label: l.kind_label, count: 0 });
  }
  for (const l of applyFilters(letters, { ...f, kinds: [] })) {
    const seen = counts.get(l.kind);
    if (seen) seen.count += 1;
    else counts.set(l.kind, { value: l.kind, label: l.kind_label, count: 1 });
  }
  return [...counts.values()].sort((a, b) => b.count - a.count || a.label.localeCompare(b.label));
}

export function toggle(list: string[], value: string): string[] {
  return list.includes(value) ? list.filter((v) => v !== value) : [...list, value];
}

export function activeFilterCount(f: Filters): number {
  return f.kinds.length + (f.printed === "all" ? 0 : 1) + (f.search.trim() ? 1 : 0);
}

export function statusLabel(printed: boolean): string {
  return printed ? "Printed" : "Not printed";
}

export type SortKey = "letter_date" | "kind_label" | "account_id" | "amount" | "printed";
export type SortDir = "asc" | "desc";

/** Amounts sort as numbers (they arrive as text) with a missing one last either way. */
export function sortLetters(letters: LetterSummary[], key: SortKey, dir: SortDir): LetterSummary[] {
  const sign = dir === "asc" ? 1 : -1;
  return [...letters].sort((a, b) => {
    if (key === "amount") {
      const x = amountValue(a.amount), y = amountValue(b.amount);
      if (x === null || y === null) return x === y ? 0 : x === null ? 1 : -1;
      return sign * (x - y);
    }
    if (key === "printed") return sign * (Number(a.printed) - Number(b.printed));
    return sign * String(a[key] ?? "").localeCompare(String(b[key] ?? ""));
  });
}

/** The line a reviewer checks first: how many letters, for how many accounts, worth how much. */
export function totals(letters: LetterSummary[]): { letters: number; accounts: number; amount: number; notPrinted: number } {
  return {
    letters: letters.length,
    accounts: new Set(letters.map((l) => l.account_id)).size,
    amount: letters.reduce((sum, l) => sum + (amountValue(l.amount) ?? 0), 0),
    notPrinted: letters.filter((l) => !l.printed).length,
  };
}

/** Money with cents always shown, so a right-aligned column lines up. */
export function formatAmount(value: Money | undefined): string {
  const n = amountValue(value);
  return n === null
    ? "—"
    : n.toLocaleString("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

/** The server's ceiling (MAX_WINDOW_DAYS in api/letters/routes.py), checked before calling it. */
export const MAX_WINDOW_DAYS = 366;
const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

export function validateWindow(from: string, to: string): string | null {
  const start = Date.parse(from), end = Date.parse(to);
  if (!ISO_DATE.test(from) || !ISO_DATE.test(to) || Number.isNaN(start) || Number.isNaN(end)) {
    return "Choose a start date and an end date.";
  }
  if (end < start) return "The start date is after the end date.";
  // Both parse as UTC midnight, so the difference is whole days, as the server counts them.
  if ((end - start) / 86_400_000 >= MAX_WINDOW_DAYS) {
    return `A window covers at most ${MAX_WINDOW_DAYS} days; choose a shorter one.`;
  }
  return null;
}

export function letterErrorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 403) return "Your access does not include letters.";
    if (err.status === 501) return "Letters are not available for this organization yet.";
    if (err.status === 422) return "That window reads too many rows; choose a shorter one.";
  }
  return err instanceof Error && err.message ? err.message : "The letters could not be loaded. Try again.";
}
