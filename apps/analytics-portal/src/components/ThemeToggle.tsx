"use client";

import { useColorMode } from "@/components/PortalThemeProvider";

export function ThemeToggle() {
  const { colorMode, toggleColorMode } = useColorMode();

  return (
    <button
      type="button"
      onClick={toggleColorMode}
      className="btn-ghost px-2.5 py-2"
      aria-label={colorMode === "dark" ? "Switch to light mode" : "Switch to dark mode"}
      title={colorMode === "dark" ? "Light mode" : "Dark mode"}
    >
      {colorMode === "dark" ? (
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden>
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
          />
        </svg>
      ) : (
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden>
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
          />
        </svg>
      )}
    </button>
  );
}
