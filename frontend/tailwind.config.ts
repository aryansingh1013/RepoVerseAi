import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        void: {
          950: "#05070d",
          900: "#080b14",
          800: "#0d1220",
          700: "#141b2e",
          600: "#1c2540",
        },
        signal: {
          400: "#7fb8ff",
          500: "#4d8fdd",
          600: "#2f6bb8",
        },
        ember: {
          400: "#ff9d5c",
          500: "#e8823a",
        },
        mist: {
          100: "#e8ecf5",
          300: "#aab4cc",
          500: "#6b7593",
          700: "#3f4660",
        },
      },
      fontFamily: {
        display: ["'Space Grotesk'", "sans-serif"],
        body: ["'Inter'", "sans-serif"],
        mono: ["'JetBrains Mono'", "monospace"],
      },
      boxShadow: {
        glow: "0 0 24px rgba(127, 184, 255, 0.25)",
      },
      keyframes: {
        pulseSlow: {
          "0%, 100%": { opacity: "0.4" },
          "50%": { opacity: "1" },
        },
        drift: {
          "0%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-4px)" },
          "100%": { transform: "translateY(0px)" },
        },
      },
      animation: {
        "pulse-slow": "pulseSlow 3s ease-in-out infinite",
        drift: "drift 6s ease-in-out infinite",
      },
    },
  },
  plugins: [],
} satisfies Config;
