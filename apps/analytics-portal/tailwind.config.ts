/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: "class",
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        // Soul Palette V2.1 uses the shadcn token NAMES, and our vendored shadcn
        // components (ui/chart.tsx) style themselves with bg-background,
        // fill-muted, text-muted-foreground, border-border. Those classes were
        // never registered, so they silently did nothing and recharts fell back to
        // its own light-grey defaults -- a near-white tooltip and hover cursor that
        // was unreadable on the dark theme. Registering them makes the vendored
        // components theme-aware for free.
        background: "var(--background)",
        foreground: "var(--foreground)",
        card: { DEFAULT: "var(--card)", foreground: "var(--foreground)" },
        popover: { DEFAULT: "var(--card)", foreground: "var(--foreground)" },
        muted: { DEFAULT: "var(--muted)", foreground: "var(--muted-foreground)" },
        border: "var(--border)",
        input: "var(--input)",
        ring: "var(--ring)",
        brand: {
          DEFAULT: "var(--brand)",
          navy: "var(--brand-navy)",
          blue: {
            1: "var(--brand-blue-1)",
            2: "var(--brand-blue-2)",
            3: "var(--brand-blue-3)",
          },
          teal: {
            1: "var(--brand-teal-1)",
            2: "var(--brand-teal-2)",
            3: "var(--brand-teal-3)",
          },
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
        heading: {
          DEFAULT: "var(--heading)",
          accent: "var(--heading-accent)",
        },
        // Status pairs from the palette: a foreground and the ground it sits on,
        // contrast-verified together. Use these instead of emerald/red/amber classes.
        ok: { DEFAULT: "var(--ok)", bg: "var(--ok-bg)" },
        over: { DEFAULT: "var(--over)", bg: "var(--over-bg)" },
        warn: { DEFAULT: "var(--warn-fg)", bg: "var(--warn-bg)" },
        primary: {
          DEFAULT: "var(--primary)",
          fg: "var(--primary-foreground)",
        },
        band: "var(--band)",
        neutral: {
          0: "var(--neutral-0)", 1: "var(--neutral-1)", 2: "var(--neutral-2)",
          3: "var(--neutral-3)", 4: "var(--neutral-4)", 5: "var(--neutral-5)",
          6: "var(--neutral-6)",
        },
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
          6: "var(--chart-6)",
          selected: "var(--chart-selected)",
        },
      },
    },
  },
  plugins: [],
};
