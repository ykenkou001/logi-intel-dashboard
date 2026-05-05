import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Logi-Intel CLO Report デザイントークンに合わせた配色
        // 詳細は docs/ppt_design.md / DESIGN.md を参照
        primary: {
          DEFAULT: "#1F4E79", // ネイビー基調
          light: "#2E73AC",
          dark: "#0F2D4F",
        },
        accent: {
          DEFAULT: "#C00000", // 警告・主要数値の強調
          light: "#E63946",
        },
        muted: {
          DEFAULT: "#666666",
          light: "#9E9E9E",
          bg: "#F5F5F5",
        },
      },
    },
  },
  plugins: [],
};

export default config;
