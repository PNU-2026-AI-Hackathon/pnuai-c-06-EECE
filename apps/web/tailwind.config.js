/**
 * 토스 계열 톤. 흰 표면 · 넓은 여백 · 부드러운 라운드 · 얇은 회색 선.
 * 색은 역할로 부른다 (bg / surface / ink / sub / line / brand / crit / warn / ok).
 * 판정 색(crit · warn · ok)은 API_CONTRACT.md 의 severity · status 와 1:1로 맞춘다.
 */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#F7F8FA", // 페이지 바탕
        surface: "#FFFFFF", // 카드 · 시트
        "surface-2": "#F2F4F6", // 카드 안에서 한 단 낮은 면 (코드 발췌 등)
        ink: "#191F28", // 본문
        sub: "#4E5968", // 보조 텍스트
        mute: "#8B95A1", // 더 흐린 텍스트 · 비활성
        line: "#E5E8EB", // 경계선
        brand: "#3182F6", // 강조
        "brand-strong": "#1B64DA", // 버튼 · 링크 (작은 글씨에도 대비 확보)
        "brand-weak": "#EBF3FE",
        crit: "#D6293E", // CRITICAL
        "crit-weak": "#FEECEE",
        warn: "#B45309", // WARNING · skipped
        "warn-weak": "#FFF4E5",
        ok: "#087A57", // PASS · cleared · done
        "ok-weak": "#E6F7F1",
      },
      fontFamily: {
        sans: ["'Pretendard Variable'", "Pretendard", "-apple-system", "system-ui", "sans-serif"],
        mono: ["'JetBrains Mono'", "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      borderRadius: {
        card: "20px",
        block: "12px",
        chip: "8px",
      },
      boxShadow: {
        card: "0 1px 2px rgba(25,31,40,.04), 0 8px 24px rgba(25,31,40,.06)",
        pop: "0 2px 4px rgba(25,31,40,.05), 0 12px 32px rgba(25,31,40,.10)",
        brand: "0 8px 20px rgba(49,130,246,.24)",
      },
      letterSpacing: { tight: "-0.02em" },
    },
  },
  plugins: [],
};
