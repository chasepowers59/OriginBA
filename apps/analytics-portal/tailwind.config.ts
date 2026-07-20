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
      },
    },
  },
  plugins: [],
};
