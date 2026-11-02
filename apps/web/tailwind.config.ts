import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0b111e", // Deep navy
        surface: "#121b2d",
        "surface-card": "#18243c",
        border: "#20304f",
        primary: "#10b981",    // Agri Green
        accent: "#06b6d4",     // Precision Cyan
        warning: "#f59e0b",    // Amber inspect
        danger: "#ef4444",     // Red act
      },
    },
  },
  plugins: [],
};
export default config;

