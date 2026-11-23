/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,jsx,ts,tsx}", "./app/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        surface: { 0: "#F3F8F5", 1: "#FFFFFF", 2: "#E9F2EC" },
        panel: "#FFFFFF",
        fg: { DEFAULT: "#0F241A", muted: "#5A7166", dim: "#8CA096" },
        ink: "#0A1F16",
        line: "#DCE8E1",
        accent: {
          DEFAULT: "#0E8A5F",
          dark: "#0A5C41",
          dim: "#D6EFE2",
          soft: "#EDF8F2",
          light: "#7FD3AE",
        },
        up: "#0E9F6E",
        down: "#D14343",
        warn: "#B07D1A",
      },
      fontFamily: {
        sans: ["Inter", "Inter var", "Segoe UI", "system-ui", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "JetBrains Mono", "Consolas", "monospace"],
      },
      fontSize: {
        xs: ["0.75rem", { lineHeight: "1.05rem" }],
        sm: ["0.875rem", { lineHeight: "1.35rem" }],
        base: ["1rem", { lineHeight: "1.55rem" }],
        lg: ["1.125rem", { lineHeight: "1.6rem" }],
        xl: ["1.35rem", { lineHeight: "1.75rem" }],
      },
      borderRadius: {
        xl: "0.9rem",
        "2xl": "1.15rem",
        "3xl": "1.5rem",
      },
      boxShadow: {
        glass:
          "inset 0 1px 0 rgba(255,255,255,0.9), 0 18px 44px -30px rgba(9,56,38,0.45)",
        lift:
          "inset 0 1px 0 rgba(255,255,255,0.9), 0 26px 52px -28px rgba(9,56,38,0.42)",
        emerald: "0 10px 24px -12px rgba(10,107,73,0.65)",
        ring: "0 0 0 4px rgba(14,138,95,0.12)",
      },
      backgroundImage: {
        "emerald-mesh":
          "radial-gradient(1100px 700px at 5% -5%, rgba(14,138,95,0.16), transparent 60%), radial-gradient(900px 600px at 100% 0%, rgba(127,211,174,0.22), transparent 55%), linear-gradient(180deg, #F8FBF9 0%, #EEF6F1 55%, #F6FBF8 100%)",
        "emerald-cta": "linear-gradient(135deg, #12996A 0%, #0A6B49 100%)",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          "100%": { transform: "translateX(100%)" },
        },
        "slide-in": {
          "0%": { opacity: "0", transform: "translateX(-16px)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
        "pulse-soft": {
          "0%, 100%": { opacity: "1", transform: "scale(1)" },
          "50%": { opacity: "0.55", transform: "scale(0.9)" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.5s cubic-bezier(0.22,1,0.36,1) both",
        shimmer: "shimmer 1.6s infinite",
        "pulse-soft": "pulse-soft 2.2s ease-in-out infinite",
        "slide-in": "slide-in 0.28s cubic-bezier(0.22,1,0.36,1) both",
      },
      transitionTimingFunction: {
        smooth: "cubic-bezier(0.22, 1, 0.36, 1)",
      },
    },
  },
  darkMode: "class",
  corePlugins: { preflight: true },
  plugins: [],
};
