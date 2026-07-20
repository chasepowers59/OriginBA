import type { PortalBrandConfig } from "./types";

/** Default brand tokens — overridden at runtime by portal client config. */
export const DEFAULT_BRAND: PortalBrandConfig = {
  name: "OriginBA",
  product: "Utility Insights",
  tagline: "Modern analytics for water, electric, and gas utilities",
  logo_initials: "BA",
  logo_src: "/brand-icon.svg",
  connection_label: "Connected",
  footer: "Trusted snapshot data · refreshed on schedule · ready for council and regulator reporting",
};

/** Runtime brand (set by PortalThemeProvider). Falls back to defaults. */
export let BRAND: PortalBrandConfig = { ...DEFAULT_BRAND };

export function applyBrandConfig(brand: Partial<PortalBrandConfig>): void {
  BRAND = { ...DEFAULT_BRAND, ...brand };
}
