import type { Config } from "tailwindcss";

const config = {
  darkMode: ["class"],
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    container: { center: true, padding: "2rem", screens: { "2xl": "1400px" } },
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: { DEFAULT: "hsl(var(--primary))", foreground: "hsl(var(--primary-foreground))" },
        secondary: { DEFAULT: "hsl(var(--secondary))", foreground: "hsl(var(--secondary-foreground))" },
        destructive: { DEFAULT: "hsl(var(--destructive))", foreground: "hsl(var(--destructive-foreground))" },
        muted: { DEFAULT: "hsl(var(--muted))", foreground: "hsl(var(--muted-foreground))" },
        accent: { DEFAULT: "hsl(var(--accent))", foreground: "hsl(var(--accent-foreground))" },
        popover: { DEFAULT: "hsl(var(--popover))", foreground: "hsl(var(--popover-foreground))" },
        card: { DEFAULT: "hsl(var(--card))", foreground: "hsl(var(--card-foreground))" },
        /** 증가 — 채도를 낮춘 초록. 색 단독으로 의미를 전달하지 않는다 */
        up: { DEFAULT: "hsl(var(--up))", soft: "hsl(var(--up-soft))" },
        /** 감소 — 채도를 낮춘 빨강 */
        down: { DEFAULT: "hsl(var(--down))", soft: "hsl(var(--down-soft))" },
        /** 포인트 컬러의 옅은 배경 */
        "brand-soft": "hsl(var(--brand-soft))",
      },
      fontSize: {
        /** 결론을 말하는 문장형 헤드라인 */
        headline: ["1.75rem", { lineHeight: "1.4", fontWeight: "600", letterSpacing: "-0.02em" }],
        /** 핵심 지표용 — 32px 이상 */
        metric: ["2.25rem", { lineHeight: "1.15", fontWeight: "700", letterSpacing: "-0.03em" }],
        "metric-lg": ["3rem", { lineHeight: "1.1", fontWeight: "700", letterSpacing: "-0.03em" }],
      },
      height: { 13: "3.25rem" },
      borderRadius: {
        /* 카드 16px · 버튼 14px · 작은 요소 10px */
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 6px)",
      },
      keyframes: {
        "accordion-down": { from: { height: "0" }, to: { height: "var(--radix-accordion-content-height)" } },
        "accordion-up": { from: { height: "var(--radix-accordion-content-height)" }, to: { height: "0" } },
      },
      animation: { "accordion-down": "accordion-down 0.2s ease-out", "accordion-up": "accordion-up 0.2s ease-out" },
    },
  },
  plugins: [require("tailwindcss-animate")],
} satisfies Config;

export default config;
