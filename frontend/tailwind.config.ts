import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#fff5ed",
          100: "#ffe6d5",
          200: "#ffc9aa",
          300: "#ffa270",
          400: "#ff7b3d",
          500: "#ff641a",
          600: "#ed4f0c",
          700: "#c43b0a",
          800: "#9c3010",
          900: "#7e2a10",
          950: "#441207",
        },
        navy: {
          50: "#eef4ff",
          100: "#d9e6ff",
          200: "#b9d1ff",
          300: "#8eb2ff",
          400: "#5c89f5",
          500: "#3767db",
          600: "#254db7",
          700: "#1f3d91",
          800: "#1d3473",
          900: "#172951",
          950: "#06152f",
        },
        ink: "#07162f",
      },
      fontFamily: {
        sans: [
          "ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Roboto",
          "Helvetica Neue", "Arial", "sans-serif",
        ],
      },
      boxShadow: {
        card: "0 8px 30px rgba(6, 21, 47, .08)",
        soft: "0 14px 40px rgba(6, 21, 47, .12)",
        glow: "0 12px 36px rgba(255, 100, 26, .24)",
      },
      borderRadius: {
        xl2: "1.25rem",
      },
      backgroundImage: {
        "hero-radial": "radial-gradient(circle at 70% 20%, rgba(55,103,219,.20), transparent 36%), radial-gradient(circle at 92% 82%, rgba(255,100,26,.18), transparent 28%)",
      },
    },
  },
  plugins: [],
};
export default config;
