import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const read = (f: string) => readFileSync(resolve(__dirname, f), "utf8");
const px = (tailwindStep: string) => Number(tailwindStep) * 4;

describe("the floating Ask Ori button", () => {
  it("clears the page's last content by a row, with room to spare", () => {
    const main = read("AppShell.tsx").match(/<main className="[^"]*\bpb-(\d+)\b/);
    const button = read("AssistantDrawer.tsx").match(/md:bottom-(\d+)\b/);
    expect(main && button).toBeTruthy();
    // Desktop: py-2.5 around the 28px (h-7) mark disc = 48px tall.
    const buttonTop = px(button![1]) + 48;
    expect(px(main![1])).toBeGreaterThanOrEqual(buttonTop + 24);
  });
});
