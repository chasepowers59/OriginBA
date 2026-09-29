import { describe, expect, it } from "vitest";
import { BUILDER_AXIS, SPARK_AXIS, chartLayout, piePlan } from "./chartLayout";

const CLASSES = [
  "Electric Residential",
  "Electric Commercial",
  "Water Residential",
  "Waste Water Residential",
  "Gas Commercial",
  "Street Lighting",
  "Irrigation",
  "Fire Service",
];

/** Average glyph advance the layout budgets with; a tick must fit its slot at it. */
const charPx = (fontSize: number) => fontSize * 0.6;

describe("chartLayout: when a chart says nothing, say so in words (UI-14)", () => {
  /**
   * A KPI of 0 drew a dashed "No trend data" box, an all-zero result drew an empty
   * $0-$4 axis, and a one-group result drew a single fat bar: each looked broken while
   * the data was fine. None of them is a comparison, so none of them is a chart.
   */
  const base = { ...BUILDER_AXIS, width: 900 };

  it("draws nothing for one group and names the group", () => {
    const out = chartLayout({ ...base, labels: ["Residential"], values: [1234] });
    expect(out.showChart).toBe(false);
    expect(out.note).toBe("Nothing to compare: one group (Residential).");
  });

  it("draws nothing when every value is zero, including zero sent as text", () => {
    const out = chartLayout({ ...base, labels: ["A", "B", "C"], values: [0, "0.00", 0] });
    expect(out.showChart).toBe(false);
    expect(out.note).toBe("Every value is zero.");
  });

  it("does not call missing values zero", () => {
    const out = chartLayout({ ...base, labels: ["A", "B"], values: [null, ""] });
    expect(out.showChart).toBe(false);
    expect(out.note).toBe("No values recorded.");
  });

  it("says there is nothing to break down when there are no groups", () => {
    const out = chartLayout({ ...SPARK_AXIS, width: 300, labels: [], values: [] });
    expect(out.showChart).toBe(false);
    expect(out.note).toBe("No breakdown to show.");
  });

  it("draws a chart for two groups with a real value", () => {
    const out = chartLayout({ ...base, labels: ["A", "B"], values: [0, -5] });
    expect(out.showChart).toBe(true);
    expect(out.note).toBeNull();
  });
});

describe("chartLayout: KPI spark charts (UI-7)", () => {
  // 320 px phone: 16 px page gutters and the card's own padding leave about 270 px.
  const phone = 270;

  it("reads at 10-11 px", () => {
    expect(SPARK_AXIS.fontSize).toBeGreaterThanOrEqual(10);
    expect(SPARK_AXIS.fontSize).toBeLessThanOrEqual(11);
  });

  it("keeps up to five categories as columns with a two-line axis about 36 px tall", () => {
    const labels = CLASSES.slice(0, 5);
    const out = chartLayout({ ...SPARK_AXIS, width: phone, labels, values: [5, 4, 3, 2, 1] });
    expect(out.orientation).toBe("vertical");
    expect(out.tickLines.some((lines) => lines.length === 2)).toBe(true);
    expect(out.axisSize).toBeGreaterThanOrEqual(34);
    expect(out.axisSize).toBeLessThanOrEqual(38);
  });

  it("never lets a tick line overflow its column at 320 px", () => {
    for (let n = 2; n <= 5; n++) {
      const labels = CLASSES.slice(0, n);
      const out = chartLayout({ ...SPARK_AXIS, width: phone, labels, values: labels.map((_, i) => i + 1) });
      const slot = (phone - SPARK_AXIS.valueAxisWidth) / n;
      for (const lines of out.tickLines) {
        for (const line of lines) expect(line.length * charPx(SPARK_AXIS.fontSize)).toBeLessThanOrEqual(slot);
      }
    }
  });

  it("switches to horizontal bars above five categories", () => {
    const labels = CLASSES.slice(0, 6);
    const out = chartLayout({ ...SPARK_AXIS, width: 600, labels, values: [6, 5, 4, 3, 2, 1] });
    expect(out.orientation).toBe("horizontal");
    for (const lines of out.tickLines) expect(lines).toHaveLength(1);
  });

  it("uses a one-line axis when every label fits on one line", () => {
    const out = chartLayout({ ...SPARK_AXIS, width: phone, labels: ["Gas", "Water"], values: [1, 2] });
    expect(out.tickLines).toEqual([["Gas"], ["Water"]]);
    expect(out.axisSize).toBeLessThan(30);
  });
});

describe("chartLayout: the explorer and builder chart (UI-8)", () => {
  it("keeps six categories as columns on a wide chart, every one labelled", () => {
    const labels = CLASSES.slice(0, 6);
    const out = chartLayout({ ...BUILDER_AXIS, width: 900, labels, values: [6, 5, 4, 3, 2, 1] });
    expect(out.orientation).toBe("vertical");
    expect(out.tickLines).toHaveLength(6);
    expect(out.tickLines.every((lines) => lines.join("").length > 0)).toBe(true);
  });

  it("uses horizontal bars above six categories so no label has to be hidden", () => {
    const labels = CLASSES.slice(0, 7);
    const out = chartLayout({ ...BUILDER_AXIS, width: 1200, labels, values: labels.map((_, i) => i + 1) });
    expect(out.orientation).toBe("horizontal");
    expect(out.tickLines).toHaveLength(7);
  });

  it("uses horizontal bars when the columns are too narrow to read, as on a phone", () => {
    const labels = CLASSES.slice(0, 5);
    const out = chartLayout({ ...BUILDER_AXIS, width: 260, labels, values: [5, 4, 3, 2, 1] });
    expect(out.orientation).toBe("horizontal");
  });

  it("keeps short labels as columns even when narrow", () => {
    const out = chartLayout({ ...BUILDER_AXIS, width: 260, labels: ["True", "False"], values: [3, 9] });
    expect(out.orientation).toBe("vertical");
  });

  it("honours a reader who chose horizontal bars", () => {
    const out = chartLayout({ ...BUILDER_AXIS, horizontal: true, width: 900, labels: ["A", "B"], values: [1, 2] });
    expect(out.orientation).toBe("horizontal");
  });

  it("sizes the row-label axis to its longest line, within 40% of the chart", () => {
    const labels = CLASSES.slice(0, 7);
    const out = chartLayout({ ...BUILDER_AXIS, width: 320, labels, values: labels.map((_, i) => i + 1) });
    expect(out.axisSize).toBeLessThanOrEqual(320 * 0.4);
    const longest = Math.max(...out.tickLines.flat().map((line) => line.length));
    expect(out.axisSize).toBeGreaterThanOrEqual(longest * charPx(BUILDER_AXIS.fontSize));
  });

  it("leaves room for uppercase codes as they render, not at the average glyph", () => {
    // Widths of the portal's tick font (Aptos stack) in Chrome, 2026-09-29. Capitals run
    // ~0.68em against the 0.6em average, so "DISCONNECT-METER" was clipped on home.
    const rendered: Record<number, Record<string, number>> = {
      10: { "DISCONNECT-METER": 103.9, "ERT-EXCHANGE-W": 91.8, "SUB-CORRECT": 72.6, "MIMO-R": 39.4 },
      11: { "DISCONNECT-METER": 114.3, "ERT-EXCHANGE-W": 101, "SUB-CORRECT": 79.9, "MIMO-R": 43.4 },
    };
    // recharts draws a row label tickSize (6) + tickMargin (2) inside the axis edge.
    const TICK_OFFSET = 8;
    for (const preset of [SPARK_AXIS, BUILDER_AXIS]) {
      const labels = [...Object.keys(rendered[preset.fontSize]), "A", "B", "C"];
      const out = chartLayout({ ...preset, width: 600, labels, values: labels.map((_, i) => i + 1) });
      expect(out.orientation).toBe("horizontal");
      for (const [label, px] of Object.entries(rendered[preset.fontSize])) {
        expect(out.tickLines[labels.indexOf(label)]).toEqual([label]);
        expect(out.axisSize).toBeGreaterThanOrEqual(px + TICK_OFFSET);
      }
    }
  });

  it("decides by count alone before the chart has been measured", () => {
    const out = chartLayout({ ...BUILDER_AXIS, width: 0, labels: CLASSES.slice(0, 3), values: [1, 2, 3] });
    expect(out.orientation).toBe("vertical");
  });
});

describe("piePlan: a pie only while it stays readable (UI-15)", () => {
  /**
   * The chart palette has five colours, and past five slices they repeated: two
   * different groups in one colour. At most four named slices plus "Other" keeps every
   * colour distinct, and "Other" is only honest while it is no bigger than a slice it
   * sits beside; otherwise the pie hides the answer and bars show every group.
   */
  it("shows every slice up to five", () => {
    const plan = piePlan(["A", "B", "C", "D", "E"], [50, 20, 15, 10, 5]);
    expect(plan.note).toBeNull();
    expect(plan.slices?.map((s) => s.label)).toEqual(["A", "B", "C", "D", "E"]);
  });

  it("folds a small tail into Other beside the four largest", () => {
    const plan = piePlan(["A", "B", "C", "D", "E", "F", "G"], [70, 12, 8, 5, 2, 2, 1]);
    expect(plan.note).toBeNull();
    expect(plan.slices).toEqual([
      { label: "A", value: 70 },
      { label: "B", value: 12 },
      { label: "C", value: 8 },
      { label: "D", value: 5 },
      { label: "Other (3)", value: 5 },
    ]);
  });

  it("prefers bars when Other would outweigh a named slice", () => {
    const labels = ["A", "B", "C", "D", "E", "F", "G"];
    const plan = piePlan(labels, [15, 15, 14, 14, 14, 14, 14]);
    expect(plan.slices).toBeNull();
    expect(plan.note).toBe("Shown as bars: 7 groups are too many for a readable pie.");
  });

  it("prefers bars when a value is negative", () => {
    const plan = piePlan(["Charges", "Adjustments"], [100, -20]);
    expect(plan.slices).toBeNull();
    expect(plan.note).toBe("Shown as bars: a pie cannot show negative values.");
  });

  it("leaves out zero slices, which have no share to draw", () => {
    const plan = piePlan(["A", "B", "C"], [3, 0, 1]);
    expect(plan.slices?.map((s) => s.label)).toEqual(["A", "C"]);
  });

  it("never draws more than five slices, so no two share a colour", () => {
    for (let n = 1; n <= 30; n++) {
      const labels = Array.from({ length: n }, (_, i) => `Group ${i}`);
      const values = labels.map((_, i) => 2 ** (n - i));
      const plan = piePlan(labels, values);
      if (plan.slices) expect(plan.slices.length).toBeLessThanOrEqual(5);
    }
  });
});
