/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: "class",
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        originba: {
          navy: "#0b1f3a",
          blue: "#1d4ed8",
          sky: "#0ea5e9",
          slate: "#64748b",
        },
        brand: {
          50: "#eff6ff",
          600: "#1d4ed8",
          700: "#1e40af",
          900: "#0b1f3a",
        },
        // Semantic theme tokens (defined in globals.css, light + dark aware). Registering
        // them here lets components use idiomatic Tailwind classes (text-fg-muted,
        // border-edge-subtle, bg-surface-subtle) instead of hardcoded slate/white classes
        // remapped by the globals.css compatibility shim.
        fg: {
          DEFAULT: "var(--foreground)",
          muted: "var(--foreground-muted)",
          subtle: "var(--foreground-subtle)",
        },
        heading: "var(--heading)",
        surface: {
          DEFAULT: "var(--surface)",
          subtle: "var(--surface-subtle)",
          solid: "var(--surface-solid)",
          input: "var(--surface-input)",
        },
        edge: {
          DEFAULT: "var(--border)",
          subtle: "var(--border-subtle)",
        },
        chip: {
          DEFAULT: "var(--chip-bg)",
          text: "var(--chip-text)",
          border: "var(--chip-border)",
        },
        accent: {
          DEFAULT: "var(--accent)",
          2: "var(--accent-2)",
          muted: "var(--accent-muted)",
        },
        chart: {
          1: "var(--chart-1)",
          2: "var(--chart-2)",
          3: "var(--chart-3)",
          4: "var(--chart-4)",
          5: "var(--chart-5)",
          selected: "var(--chart-selected)",
        },
      },
    },
  },
  plugins: [],
};
