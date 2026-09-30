import { describe, expect, it } from "vitest";
import {
  PRESENTATION_CLASS,
  enterPresentation,
  exitPresentation,
  isPresenting,
  toolbarControls,
} from "./presentationMode";

/**
 * Presentation mode had no way out.
 *
 *   globals.css   html.presentation-mode .no-print { display: none !important }
 *   toolbar       <div className="no-print ..."> Present | Export | Exit present </div>
 *
 * So entering presentation hid the whole toolbar INCLUDING its own "Exit present"
 * button. Measured on /workstream/billing: with the class applied, offsetParent was
 * null for both buttons. And nothing listened for `fullscreenchange`, so pressing
 * Escape -- the natural way to leave fullscreen -- dropped fullscreen while leaving
 * the class on the root, stranding the app in a stripped-down layout until a reload.
 *
 * Both buttons also rendered unconditionally, so "Exit present" sat there permanently
 * even when nothing was being presented.
 *
 * The root is injected so this is testable under the "node" vitest environment
 * (no jsdom in this project) -- and so the same logic can be driven from a test, the
 * component, and the fullscreen/Escape listeners without three copies of it.
 */
function fakeRoot() {
  const classes = new Set<string>();
  return {
    classList: {
      add: (c: string) => void classes.add(c),
      remove: (c: string) => void classes.delete(c),
      contains: (c: string) => classes.has(c),
    },
    _classes: classes,
  };
}

describe("presentation mode state", () => {
  it("enters and reports itself", () => {
    const root = fakeRoot();
    expect(isPresenting(root)).toBe(false);
    enterPresentation(root);
    expect(root._classes.has(PRESENTATION_CLASS)).toBe(true);
    expect(isPresenting(root)).toBe(true);
  });

  it("exits, which is the part that was unreachable", () => {
    const root = fakeRoot();
    enterPresentation(root);
    exitPresentation(root);
    expect(isPresenting(root)).toBe(false);
  });

  it("is idempotent in both directions", () => {
    const root = fakeRoot();
    enterPresentation(root);
    enterPresentation(root);
    expect(root._classes.size).toBe(1);
    exitPresentation(root);
    exitPresentation(root);
    expect(isPresenting(root)).toBe(false);
  });

  it("survives an exit that was never entered", () => {
    const root = fakeRoot();
    expect(() => exitPresentation(root)).not.toThrow();
    expect(isPresenting(root)).toBe(false);
  });
});

describe("toolbarControls", () => {
  it("never offers Present and Exit at the same time", () => {
    for (const presenting of [true, false]) {
      const c = toolbarControls(presenting);
      expect(c.showPresent && c.showExit).toBe(false);
      expect(c.showPresent || c.showExit).toBe(true);
    }
  });

  it("offers Present when idle, Exit when presenting", () => {
    expect(toolbarControls(false)).toMatchObject({ showPresent: true, showExit: false });
    expect(toolbarControls(true)).toMatchObject({ showPresent: false, showExit: true });
  });

  it("hides the export actions while presenting -- they are not a slide", () => {
    expect(toolbarControls(true).showExports).toBe(false);
    expect(toolbarControls(false).showExports).toBe(true);
  });

  it("keeps the exit control out of the class presentation mode hides", () => {
    // The exit affordance must not live inside .no-print, which is exactly how it
    // hid itself. The component asserts this by using this flag for its wrapper.
    expect(toolbarControls(true).exitEscapesNoPrint).toBe(true);
  });
});
