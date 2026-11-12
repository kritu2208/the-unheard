/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#111111",
        surface: "#191716",
        ivory: "#F3EFE7",
        burgundy: "#681F2B",
        crimson: "#B43A46",
        "muted-text": "#A6A09A",
      },
      fontFamily: {
        serif: ['"Newsreader"', "Georgia", "Cambria", "Times New Roman", "serif"],
        sans: ['"Inter"', "system-ui", "-apple-system", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "SFMono-Regular", "monospace"],
      },
    },
  },
  plugins: [],
};

