import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { RuleCard, SummaryCard, type DqRule } from "./DataQualityBoard";
import { HealthTable } from "./SystemHealthPanel";
import { LetterTypeChips } from "./letters/LettersWorkspace";

// UI-16: every count a reader sees carries separators ("4,938", never "4938").
describe("counts render with thousands separators", () => {
  it("Data Quality summary card", () => {
    const html = renderToStaticMarkup(<SummaryCard label="Act now" value={4938} tone="red" glyph="!" />);
    expect(html).toContain(">4,938<");
  });

  it("Data Quality rule badge", () => {
    const rule: DqRule = {
      id: "r", object: "CI_BILL", severity: "review", title: "Bills", action: "Check",
      columns: [], rows: [], count: 200, total: 4594,
    };
    const html = renderToStaticMarkup(<RuleCard rule={rule} defaultOpen={false} onMark={async () => {}} />);
    expect(html).toContain(">4,594<");
  });

  it("Letters type chips", () => {
    const html = renderToStaticMarkup(
      <LetterTypeChips facets={[{ value: "A", label: "Final notice", count: 1672 }]} selected={[]} onToggle={() => {}} />,
    );
    expect(html).toContain(">1,672<");
  });

  it("System health numeric cells", () => {
    const html = renderToStaticMarkup(
      <HealthTable title="Routes" empty="" head={["Route", "Average ms"]} rows={[["/portal/home", 45034]]} />,
    );
    expect(html).toContain(">45,034<");
  });
});
