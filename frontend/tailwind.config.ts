import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: {
          DEFAULT: "#0b0d10",
          soft: "#11151a",
          panel: "#161b22",
        },
        border: {
          DEFAULT: "#1f262d",
          soft: "#2a323b",
        },
        fg: {
          DEFAULT: "#e6edf3",
          muted: "#9ba8b6",
          subtle: "#6b7785",
        },
        accent: {
          DEFAULT: "#7aa2f7",
          hover: "#9bb6f9",
        },
        danger: "#f7768e",
        warn: "#e0af68",
        ok: "#9ece6a",
      },
    },
  },
  plugins: [],
};

export default config;
