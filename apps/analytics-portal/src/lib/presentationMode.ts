/**
 * Presentation mode, and the way out of it.
 *
 * `html.presentation-mode .no-print { display: none }` hid the toolbar that carried
 * the only "Exit present" button, so presenting was a one-way door recoverable only by
 * reloading. The exit affordance must therefore live OUTSIDE `.no-print`, and leaving
 * fullscreen by any route has to clear the class.
 *
 * The root is injected so the same logic serves the component, its listeners and the
 * tests without a DOM library.
 */

export const PRESENTATION_CLASS = "presentation-mode";

export type PresentationRoot = {
  classList: {
    add(token: string): void;
    remove(token: string): void;
    contains(token: string): boolean;
  };
};

export function isPresenting(root: PresentationRoot): boolean {
  return root.classList.contains(PRESENTATION_CLASS);
}

export function enterPresentation(root: PresentationRoot): void {
  root.classList.add(PRESENTATION_CLASS);
}

export function exitPresentation(root: PresentationRoot): void {
  root.classList.remove(PRESENTATION_CLASS);
}

export type ToolbarControls = {
  showPresent: boolean;
  showExit: boolean;
  showExports: boolean;
  /** The exit control must not sit in `.no-print` — that is what hid it. */
  exitEscapesNoPrint: true;
};

export function toolbarControls(presenting: boolean): ToolbarControls {
  return {
    showPresent: !presenting,
    showExit: presenting,
    showExports: !presenting,
    exitEscapesNoPrint: true,
  };
}
