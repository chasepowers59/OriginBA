import { afterEach, describe, expect, it, vi } from "vitest";
import {
  activeFilterCount,
  applyFilters,
  formatAmount,
  kindFacets,
  letterErrorMessage,
  NO_FILTERS,
  sortLetters,
  statusLabel,
  toggle,
  totals,
  validateWindow,
  type LetterSummary,
} from "./letters";
import { ApiError } from "./apiErrors";
import { fetchLetter, fetchLetterPdf, fetchLetters } from "./api";

// Invented people and ids, never client data. Amounts arrive as STRINGS: the API serializes
// Decimal that way, so every helper below is exercised with the wire shape, not a friendlier one.
const L = (over: Partial<LetterSummary>): LetterSummary => ({
  letter_id: "CC-1", kind: "reminder", kind_label: "Past due reminder", template_code: "CIR-REG-REM",
  contact_type: "Regular debt reminder letter", letter_date: "2028-03-08", account_id: "1000000001",
  recipient: "Rivera,Alex", amount: "132.69", process_type: "Collection", process_id: "4000000001",
  next_action_on: "2028-03-18", printed: false, copies: 1, ...over,
});

const SET: LetterSummary[] = [
  L({}),
  L({ letter_id: "CC-2", kind: "disconnected", kind_label: "Service disconnected", template_code: "CIR-SP-DISCN",
      process_type: "Severance", account_id: "1000000002", recipient: "Okafor,Jamie", amount: "84.87", printed: true }),
  L({ letter_id: "CC-3", kind: "final_notice", kind_label: "Final notice", template_code: "CIR-AGY-WARN",
      process_type: "Write-Off", account_id: "1000000002", recipient: "Okafor,Jamie", amount: "256.56",
      letter_date: "2028-03-02" }),
  L({ letter_id: "ADJ-9", kind: "late_fee", kind_label: "Late payment charge", template_code: "", process_type: "",
      process_id: "", amount: "10.88", next_action_on: null, letter_date: "2028-03-20" }),
];

const ids = (letters: LetterSummary[]) => letters.map((l) => l.letter_id);

describe("search", () => {
  it("matches account, customer, letter id and type, ignoring case", () => {
    expect(ids(applyFilters(SET, { ...NO_FILTERS, search: "1000000002" }))).toEqual(["CC-2", "CC-3"]);
    expect(ids(applyFilters(SET, { ...NO_FILTERS, search: "okafor" }))).toEqual(["CC-2", "CC-3"]);
    expect(ids(applyFilters(SET, { ...NO_FILTERS, search: "adj" }))).toEqual(["ADJ-9"]);
    expect(ids(applyFilters(SET, { ...NO_FILTERS, search: "final NOTICE" }))).toEqual(["CC-3"]);
  });

  it("trims the term and treats blank as no search", () => {
    expect(ids(applyFilters(SET, { ...NO_FILTERS, search: "  okafor " }))).toEqual(["CC-2", "CC-3"]);
    expect(applyFilters(SET, { ...NO_FILTERS, search: "   " })).toHaveLength(4);
  });
});

describe("type and status filters", () => {
  it("combines letter types with the printed status", () => {
    expect(applyFilters(SET, { ...NO_FILTERS, kinds: ["reminder", "late_fee"] })).toHaveLength(2);
    expect(ids(applyFilters(SET, { ...NO_FILTERS, printed: "printed" }))).toEqual(["CC-2"]);
    expect(ids(applyFilters(SET, { ...NO_FILTERS, printed: "not_printed" }))).toEqual(["CC-1", "CC-3", "ADJ-9"]);
    expect(applyFilters(SET, { ...NO_FILTERS, kinds: ["disconnected"], printed: "not_printed" })).toHaveLength(0);
  });

  it("names the status the way a customer service desk says it", () => {
    expect(statusLabel(true)).toBe("Printed");
    expect(statusLabel(false)).toBe("Not printed");
  });

  it("counts active filters, search included", () => {
    expect(activeFilterCount(NO_FILTERS)).toBe(0);
    expect(activeFilterCount({ search: "x", kinds: ["a", "b"], printed: "printed" })).toBe(4);
    expect(activeFilterCount({ ...NO_FILTERS, search: "  " })).toBe(0);
  });

  it("toggle adds and removes", () => {
    expect(toggle([], "a")).toEqual(["a"]);
    expect(toggle(["a", "b"], "a")).toEqual(["b"]);
  });
});

describe("type facets", () => {
  it("count every type and stay clickable once one is chosen", () => {
    expect(kindFacets(SET, NO_FILTERS).map((f) => f.value).sort())
      .toEqual(["disconnected", "final_notice", "late_fee", "reminder"]);
    const narrowed = kindFacets(SET, { ...NO_FILTERS, kinds: ["reminder"] });
    expect(narrowed).toHaveLength(4);
    expect(narrowed.every((f) => f.count === 1)).toBe(true);
  });

  it("narrow by the other filters and carry the type's label", () => {
    expect(kindFacets(SET, { ...NO_FILTERS, printed: "printed" }))
      .toEqual([{ value: "disconnected", label: "Service disconnected", count: 1 }]);
  });

  it("keep a chosen type on screen at zero, so a filter still applied can still be removed", () => {
    const f = kindFacets(SET, { ...NO_FILTERS, kinds: ["final_notice"], search: "rivera" });
    expect(f.find((x) => x.value === "final_notice")).toEqual({ value: "final_notice", label: "Final notice", count: 0 });
  });
});

describe("sorting", () => {
  it("sorts amounts as numbers although they arrive as text", () => {
    // as text, "84.87" > "256.56" > "132.69" > "10.88"
    expect(ids(sortLetters(SET, "amount", "desc"))).toEqual(["CC-3", "CC-1", "CC-2", "ADJ-9"]);
    expect(ids(sortLetters(SET, "amount", "asc"))).toEqual(["ADJ-9", "CC-2", "CC-1", "CC-3"]);
  });

  it("puts a missing amount last in either direction", () => {
    const withGap = [...SET, L({ letter_id: "CC-4", amount: null })];
    expect(sortLetters(withGap, "amount", "asc").at(-1)?.letter_id).toBe("CC-4");
    expect(sortLetters(withGap, "amount", "desc").at(-1)?.letter_id).toBe("CC-4");
  });

  it("sorts dates, text and status, and never mutates its input", () => {
    const before = ids(SET);
    expect(ids(sortLetters(SET, "letter_date", "asc"))).toEqual(["CC-3", "CC-1", "CC-2", "ADJ-9"]);
    expect(sortLetters(SET, "kind_label", "asc")[0].kind_label).toBe("Final notice");
    expect(sortLetters(SET, "printed", "desc")[0].letter_id).toBe("CC-2");
    expect(ids(SET)).toEqual(before);
  });
});

describe("totals", () => {
  it("counts letters, distinct accounts, money due and the not-printed", () => {
    expect(totals(SET)).toEqual({ letters: 4, accounts: 2, amount: 485, notPrinted: 3 });
  });

  it("does not turn a missing amount into money", () => {
    expect(totals([L({ amount: null }), L({ amount: "1.10" })]).amount).toBeCloseTo(1.1);
  });
});

describe("amounts", () => {
  it("always show cents, so a right-aligned column lines up", () => {
    expect(formatAmount("84.8")).toBe("$84.80");
    expect(formatAmount(85)).toBe("$85.00");
    expect(formatAmount("1234.5")).toBe("$1,234.50");
    expect(formatAmount("0")).toBe("$0.00");
  });

  it("show a missing amount as missing, never as $0.00", () => {
    expect(formatAmount(null)).toBe("—");
    expect(formatAmount(undefined)).toBe("—");
    expect(formatAmount("")).toBe("—");
    expect(formatAmount("abc")).toBe("—");
  });
});

describe("the date window", () => {
  it("accepts a month, and a whole leap year", () => {
    expect(validateWindow("2022-08-01", "2022-08-31")).toBeNull();
    expect(validateWindow("2024-01-01", "2024-12-31")).toBeNull();
    expect(validateWindow("2022-08-01", "2022-08-01")).toBeNull();
  });

  it("refuses what the server refuses, before calling it", () => {
    // api/letters/routes.py: end < start, or (end - start).days >= 366
    expect(validateWindow("2024-01-01", "2025-01-01")).toBe("A window covers at most 366 days; choose a shorter one.");
    expect(validateWindow("2023-01-01", "2024-01-01")).toBeNull();
    expect(validateWindow("2022-08-31", "2022-08-01")).toBe("The start date is after the end date.");
  });

  it("asks for both dates when one is missing or malformed", () => {
    expect(validateWindow("", "2022-08-31")).toBe("Choose a start date and an end date.");
    expect(validateWindow("08/01/2022", "2022-08-31")).toBe("Choose a start date and an end date.");
    expect(validateWindow("2022-13-01", "2022-08-31")).toBe("Choose a start date and an end date.");
  });
});

describe("what a refusal says", () => {
  it("names the reason in plain words", () => {
    expect(letterErrorMessage(new ApiError("Forbidden", 403))).toBe("Your access does not include letters.");
    expect(letterErrorMessage(new ApiError("x", 501))).toBe("Letters are not available for this organization yet.");
    expect(letterErrorMessage(new ApiError("x", 422))).toBe("That window reads too many rows; choose a shorter one.");
  });

  it("passes the server's own sentence through otherwise", () => {
    expect(letterErrorMessage(new ApiError("No such letter in this organization.", 404)))
      .toBe("No such letter in this organization.");
    expect(letterErrorMessage(new Error("Failed to fetch"))).toBe("Failed to fetch");
    expect(letterErrorMessage("boom")).toBe("The letters could not be loaded. Try again.");
  });
});

describe("the letters API calls", () => {
  afterEach(() => vi.unstubAllGlobals());

  function signedIn(response: Response) {
    const fetchMock = vi.fn(async (_url: string, _init?: RequestInit) => response);
    vi.stubGlobal("fetch", fetchMock);
    vi.stubGlobal("window", {});
    vi.stubGlobal("sessionStorage", { getItem: () => "test-token" });
    vi.stubGlobal("document", { cookie: "portal_active_organization=demo25" });
    return fetchMock;
  }

  it("asks for a window with from and to", async () => {
    const fetchMock = signedIn(new Response(JSON.stringify({ count: 0, letters: [] })));
    await fetchLetters("2022-08-01", "2022-08-31");
    expect(fetchMock.mock.calls[0][0]).toMatch(/\/portal\/letters\?from=2022-08-01&to=2022-08-31$/);
  });

  it("carries the HTTP status on a refusal, so the page can say why", async () => {
    signedIn(new Response(JSON.stringify({ detail: "Letters are not available for this organization yet." }), { status: 501 }));
    const err = await fetchLetters("2022-08-01", "2022-08-31").catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(501);
    expect(err.message).toBe("Letters are not available for this organization yet.");
  });

  it("escapes the letter id in the path", async () => {
    const fetchMock = signedIn(new Response(JSON.stringify({})));
    await fetchLetter("CC-1/../x");
    expect(fetchMock.mock.calls[0][0]).toMatch(/\/portal\/letters\/CC-1%2F\.\.%2Fx$/);
  });

  it("fetches the PDF with the signed-in headers, never as a bare link, and reads the font headers", async () => {
    const fetchMock = signedIn(new Response(new Blob(["%PDF-1.4"], { type: "application/pdf" }), {
      headers: { "X-Letter-Font": "Helvetica", "X-Letter-Font-Note": "Line breaks can differ." },
    }));
    const pdf = await fetchLetterPdf("CC-3000000001");
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toMatch(/\/portal\/letters\/CC-3000000001\/pdf$/);
    const headers = init?.headers as Record<string, string>;
    expect(headers.Authorization).toBe("Bearer test-token");
    expect(headers["X-Organization-Id"]).toBe("demo25");
    expect(init?.cache).toBe("no-store");
    expect(pdf.font).toBe("Helvetica");
    expect(pdf.fontNote).toBe("Line breaks can differ.");
    expect(await pdf.blob.text()).toBe("%PDF-1.4");
  });

  it("has no font note when the approved face was used", async () => {
    signedIn(new Response(new Blob(["%PDF"]), { headers: { "X-Letter-Font": "DejaVu Sans" } }));
    expect((await fetchLetterPdf("CC-1")).fontNote).toBeNull();
  });

  it("refuses a PDF with the status attached", async () => {
    signedIn(new Response(JSON.stringify({ detail: "Forbidden" }), { status: 403 }));
    await expect(fetchLetterPdf("CC-1")).rejects.toMatchObject({ status: 403 });
  });
});
