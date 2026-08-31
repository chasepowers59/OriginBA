import type { PortalBrandConfig } from "./types";

/** Default brand tokens — overridden at runtime by portal client config. */
export const DEFAULT_BRAND: PortalBrandConfig = {
  name: "Origin",
  product: "Analytics",
  tagline: "Governed analytics for water, electric and gas utilities",
  logo_initials: "O",
  logo_src: "/origin-mark.png",
  connection_label: "Connected",
  footer: "Built on the Origin reporting layer · contracted models · traceable to the source column",
};

/** Runtime brand (set by PortalThemeProvider). Falls back to defaults. */
export let BRAND: PortalBrandConfig = { ...DEFAULT_BRAND };

export function applyBrandConfig(brand: Partial<PortalBrandConfig>): void {
  BRAND = { ...DEFAULT_BRAND, ...brand };
}

/** The brand line to display.
 *
 * The config keeps `name` and `product` separate so a client deployment can be
 * white-labelled -- "Acme Water · OriginBA". When they are the SAME, as they are for
 * OriginBA itself, concatenating them prints the name twice. Compose it here so every
 * surface reads the same and no component has to remember the rule.
 */
export function brandLine(brand: PortalBrandConfig = BRAND): string {
  return brand.name === brand.product ? brand.name : `${brand.name} · ${brand.product}`;
}

/** Window/tab title for an exported or printed view. */
export function brandTitle(title: string, brand: PortalBrandConfig = BRAND): string {
  return `${title} | ${brandLine(brand)}`;
}
