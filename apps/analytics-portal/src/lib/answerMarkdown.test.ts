import { describe, expect, it } from "vitest";
import { parseAnswer, parseInline } from "./answerMarkdown";

// The assistant answers in light markdown. The panel printed it raw ("**Total billed**",
// table pipes) in the first real demo run on 2026-09-28. These are the forms it actually uses.

describe("parseInline", () => {
  it("splits bold and code out of plain text", () => {
    expect(parseInline("from **frozen** segments in `rpt_bill_segment`.")).toEqual([
      { kind: "text", text: "from " },
      { kind: "bold", text: "frozen" },
      { kind: "text", text: " segments in " },
      { kind: "code", text: "rpt_bill_segment" },
      { kind: "text", text: "." },
    ]);
  });

  it("leaves an unmatched marker as plain text rather than swallowing the rest of the line", () => {
    expect(parseInline("2 ** 3 is not bold")).toEqual([{ kind: "text", text: "2 ** 3 is not bold" }]);
  });

  it("never interprets HTML: a tag is text", () => {
    expect(parseInline("<b>x</b>")).toEqual([{ kind: "text", text: "<b>x</b>" }]);
  });
});

describe("parseAnswer", () => {
  it("groups lines into paragraphs, lists and tables", () => {
    const blocks = parseAnswer(
      "**Total billed** by cycle:\n\n| Bill Cycle | Billed |\n|---|---:|\n| Cycle 1 | $1.4M |\n| Cycle 2 | $1.2M |\n\nScope:\n- Frozen only\n- 90 days ending 2026-06-18"
    );
    expect(blocks.map((b) => b.kind)).toEqual(["p", "table", "p", "ul"]);
    const table = blocks[1];
    expect(table.kind === "table" && table.header).toEqual(["Bill Cycle", "Billed"]);
    expect(table.kind === "table" && table.rows).toEqual([["Cycle 1", "$1.4M"], ["Cycle 2", "$1.2M"]]);
    expect(table.kind === "table" && table.align).toEqual(["left", "right"]);
    const list = blocks[3];
    expect(list.kind === "ul" && list.items.length).toBe(2);
  });

  it("keeps consecutive prose lines in one paragraph", () => {
    const blocks = parseAnswer("First line\nsecond line");
    expect(blocks).toHaveLength(1);
    expect(blocks[0].kind).toBe("p");
  });

  it("treats a pipe inside a sentence as prose, not a table", () => {
    expect(parseAnswer("Cycle 1 | Cycle 2 were the largest.").map((b) => b.kind)).toEqual(["p"]);
  });

  it("returns nothing for an empty answer", () => {
    expect(parseAnswer("")).toEqual([]);
    expect(parseAnswer("\n\n")).toEqual([]);
  });
});
