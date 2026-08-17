/**
 * 제도 도면 톤. 색은 API_CONTRACT.md의 토큰과 1:1로 맞춘다.
 * 모서리는 둥글리지 않는다 — borderRadius를 전부 0으로 덮는다.
 */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    borderRadius: { none: "0", DEFAULT: "0", sm: "0", md: "0", lg: "0", full: "0" },
    extend: {
      colors: {
        vellum: "#E6E9E4",
        "vellum-2": "#F2F4F0",
        ink: "#171C26",
        graphite: "#6E7683",
        hair: "#C3C9C1",
        redpen: "#C0322A",
        amber: "#A9700F",
        verify: "#2C6248",
      },
      fontFamily: {
        sans: ["'IBM Plex Sans KR'", "system-ui", "sans-serif"],
        cond: ["'IBM Plex Sans Condensed'", "'IBM Plex Sans KR'", "sans-serif"],
        mono: ["'IBM Plex Mono'", "ui-monospace", "monospace"],
      },
      letterSpacing: { label: ".16em" },
      backgroundImage: {
        /* 22px 미세 격자 — 제도 용지 */
        grid: `linear-gradient(to right, rgba(23,28,38,.035) 1px, transparent 1px),
               linear-gradient(to bottom, rgba(23,28,38,.035) 1px, transparent 1px)`,
      },
      backgroundSize: { grid: "22px 22px" },
    },
  },
  plugins: [],
};
