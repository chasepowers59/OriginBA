"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { fetchPortalConfig } from "@/lib/api";
import { applyBrandConfig, DEFAULT_BRAND } from "@/lib/brand";
import {
  applyColorMode,
  getStoredColorMode,
  resolveInitialColorMode,
  storeColorMode,
  type ColorMode,
} from "@/lib/colorMode";
import type { PortalConfig } from "@/lib/types";

const PortalConfigContext = createContext<PortalConfig | null>(null);

type ColorModeContextValue = {
  colorMode: ColorMode;
  setColorMode: (mode: ColorMode) => void;
  toggleColorMode: () => void;
};

const ColorModeContext = createContext<ColorModeContextValue | null>(null);

function applyThemeCss(theme: PortalConfig["theme"]): void {
  const root = document.documentElement;
  root.style.setProperty("--accent", theme.accent_from);
  root.style.setProperty("--accent-2", theme.accent_to);
  root.style.setProperty("--accent-muted", theme.accent_muted);
  root.style.setProperty("--mesh-glow-1", theme.mesh_glow_1);
  root.style.setProperty("--mesh-glow-2", theme.mesh_glow_2);
  root.style.setProperty("--mesh-glow-3", theme.mesh_glow_3);
}

const FALLBACK_CONFIG: PortalConfig = {
  client_id: "demo",
  organization_name: "Origin Utilities",
  brand: DEFAULT_BRAND,
  theme: {
    accent_from: "#38bdf8",
    accent_to: "#6366f1",
    accent_muted: "#0ea5e9",
    mesh_glow_1: "rgba(56, 189, 248, 0.12)",
    mesh_glow_2: "rgba(99, 102, 241, 0.14)",
    mesh_glow_3: "rgba(14, 165, 233, 0.08)",
  },
};

export function PortalThemeProvider({ children }: { children: ReactNode }) {
  const [config, setConfig] = useState<PortalConfig>(FALLBACK_CONFIG);
  const [colorMode, setColorModeState] = useState<ColorMode>(() => {
    if (typeof window === "undefined") return "light";
    return getStoredColorMode() ?? resolveInitialColorMode();
  });

  const setColorMode = useCallback((mode: ColorMode) => {
    setColorModeState(mode);
    storeColorMode(mode);
    applyColorMode(mode);
  }, []);

  const toggleColorMode = useCallback(() => {
    setColorModeState((prev) => {
      const next = prev === "dark" ? "light" : "dark";
      storeColorMode(next);
      applyColorMode(next);
      return next;
    });
  }, []);

  useEffect(() => {
    applyColorMode(colorMode);
  }, [colorMode]);

  useEffect(() => {
    fetchPortalConfig()
      .then((cfg) => {
        setConfig(cfg);
        applyBrandConfig(cfg.brand);
        applyThemeCss(cfg.theme);
      })
      .catch(() => {
        applyBrandConfig(FALLBACK_CONFIG.brand);
        applyThemeCss(FALLBACK_CONFIG.theme);
      });
  }, []);

  return (
    <ColorModeContext.Provider value={{ colorMode, setColorMode, toggleColorMode }}>
      <PortalConfigContext.Provider value={config}>{children}</PortalConfigContext.Provider>
    </ColorModeContext.Provider>
  );
}

export function usePortalConfig(): PortalConfig {
  return useContext(PortalConfigContext) ?? FALLBACK_CONFIG;
}

export function useBrand() {
  const config = usePortalConfig();
  return config.brand;
}

export function useColorMode(): ColorModeContextValue {
  const ctx = useContext(ColorModeContext);
  if (!ctx) {
    throw new Error("useColorMode must be used within PortalThemeProvider");
  }
  return ctx;
}
