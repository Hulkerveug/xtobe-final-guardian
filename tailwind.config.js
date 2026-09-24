/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        void: "#05070d",
        panel: "#0b101c",
        edge: "#1b2740",
        neon: "#22d3ee",
        danger: "#f43f5e",
        safe: "#34d399",
        warn: "#fbbf24",
      },
      fontFamily: {
        mono: ["'JetBrains Mono'", "Consolas", "monospace"],
      },
    },
  },
  plugins: [],
};
