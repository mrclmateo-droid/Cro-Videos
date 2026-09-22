import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      keyframes: {
        fadeUp: { "0%": { opacity: "0", transform: "translateY(8px)" }, "100%": { opacity: "1", transform: "none" } },
        shimmer: { "100%": { transform: "translateX(100%)" } },
        indeterminate: { "0%": { left: "-40%" }, "100%": { left: "100%" } },
      },
      animation: {
        "fade-up": "fadeUp .35s ease-out both",
        indeterminate: "indeterminate 1.3s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
export default config;
