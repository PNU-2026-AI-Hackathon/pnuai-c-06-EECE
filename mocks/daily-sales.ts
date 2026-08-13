import type { MockDailySale } from "./types";

/**
 * 2026년 2학기 일별 매출 원본 (카페 온담, 2026-08-31 ~ 2026-10-18).
 * 일요일은 정기 휴무라 데이터가 없고(null), 비 오는 날·공휴일·추석 임시휴업이 섞여 있다.
 * 매끈한 곡선이 아니라 원인 있는 변동과 원인 없는 잔변동이 함께 들어 있다.
 */
export const mockDailySales: MockDailySale[] = [
  // 1주차 — 개강주 (9/1 개강). 개강 전날은 아직 조용하다
  { date: "2026-08-31", weekday: 1, revenue: 320000, orderCount: 79, weather: "clear", note: "개강 전날" },
  { date: "2026-09-01", weekday: 2, revenue: 520000, orderCount: 124, weather: "clear", note: "2학기 개강" },
  { date: "2026-09-02", weekday: 3, revenue: 545000, orderCount: 131, weather: "cloudy", note: null },
  { date: "2026-09-03", weekday: 4, revenue: 560000, orderCount: 133, weather: "clear", note: null },
  { date: "2026-09-04", weekday: 5, revenue: 590000, orderCount: 140, weather: "clear", note: null },
  { date: "2026-09-05", weekday: 6, revenue: 380000, orderCount: 92, weather: "clear", note: null },
  { date: "2026-09-06", weekday: 0, revenue: null, orderCount: null, weather: "clear", note: "정기 휴무" },

  // 2주차 — 수요일 종일 비, 목·금 회복
  { date: "2026-09-07", weekday: 1, revenue: 480000, orderCount: 118, weather: "cloudy", note: null },
  { date: "2026-09-08", weekday: 2, revenue: 505000, orderCount: 121, weather: "clear", note: null },
  { date: "2026-09-09", weekday: 3, revenue: 430000, orderCount: 103, weather: "rain", note: "종일 비" },
  { date: "2026-09-10", weekday: 4, revenue: 540000, orderCount: 129, weather: "cloudy", note: null },
  { date: "2026-09-11", weekday: 5, revenue: 585000, orderCount: 138, weather: "clear", note: null },
  { date: "2026-09-12", weekday: 6, revenue: 365000, orderCount: 89, weather: "clear", note: null },
  { date: "2026-09-13", weekday: 0, revenue: null, orderCount: null, weather: "rain", note: "정기 휴무" },

  // 3주차 — 특별한 사건 없이 잔변동만 있는 평범한 주
  { date: "2026-09-14", weekday: 1, revenue: 512000, orderCount: 122, weather: "clear", note: null },
  { date: "2026-09-15", weekday: 2, revenue: 498000, orderCount: 119, weather: "clear", note: null },
  { date: "2026-09-16", weekday: 3, revenue: 536000, orderCount: 127, weather: "cloudy", note: null },
  { date: "2026-09-17", weekday: 4, revenue: 555000, orderCount: 130, weather: "clear", note: null },
  { date: "2026-09-18", weekday: 5, revenue: 604000, orderCount: 143, weather: "clear", note: null },
  { date: "2026-09-19", weekday: 6, revenue: 372000, orderCount: 90, weather: "cloudy", note: null },
  { date: "2026-09-20", weekday: 0, revenue: null, orderCount: null, weather: "clear", note: "정기 휴무" },

  // 4주차 — 추석 연휴(9/24~26). 목요일 단축영업 후 금·토 임시휴업
  { date: "2026-09-21", weekday: 1, revenue: 490000, orderCount: 117, weather: "clear", note: null },
  { date: "2026-09-22", weekday: 2, revenue: 470000, orderCount: 112, weather: "cloudy", note: "연휴 전 학생 귀향 시작" },
  { date: "2026-09-23", weekday: 3, revenue: 505000, orderCount: 120, weather: "clear", note: null },
  { date: "2026-09-24", weekday: 4, revenue: 210000, orderCount: 51, weather: "clear", note: "추석 연휴 시작 · 15시 단축영업" },
  { date: "2026-09-25", weekday: 5, revenue: null, orderCount: null, weather: "clear", note: "추석 임시휴업" },
  { date: "2026-09-26", weekday: 6, revenue: null, orderCount: null, weather: "rain", note: "추석 임시휴업" },
  { date: "2026-09-27", weekday: 0, revenue: null, orderCount: null, weather: "rain", note: "정기 휴무" },

  // 5주차 — 연휴 직후 복귀가 느리다. 토요일은 개천절
  { date: "2026-09-28", weekday: 1, revenue: 445000, orderCount: 108, weather: "cloudy", note: "연휴 직후 · 복귀 지연" },
  { date: "2026-09-29", weekday: 2, revenue: 520000, orderCount: 124, weather: "clear", note: null },
  { date: "2026-09-30", weekday: 3, revenue: 548000, orderCount: 130, weather: "clear", note: null },
  { date: "2026-10-01", weekday: 4, revenue: 562000, orderCount: 132, weather: "clear", note: "소금빵 16:40 품절" },
  { date: "2026-10-02", weekday: 5, revenue: 598000, orderCount: 141, weather: "clear", note: null },
  { date: "2026-10-03", weekday: 6, revenue: 295000, orderCount: 72, weather: "cloudy", note: "개천절 · 캠퍼스 인구 감소" },
  { date: "2026-10-04", weekday: 0, revenue: null, orderCount: null, weather: "clear", note: "정기 휴무" },

  // 6주차 — 예측이 크게 빗나간 주. 수요일 비 + 금요일 한글날 연휴 유출
  { date: "2026-10-05", weekday: 1, revenue: 578000, orderCount: 136, weather: "clear", note: null },
  { date: "2026-10-06", weekday: 2, revenue: 596000, orderCount: 140, weather: "clear", note: null },
  { date: "2026-10-07", weekday: 3, revenue: 452000, orderCount: 109, weather: "heavy_rain", note: "오후 내내 강한 비" },
  { date: "2026-10-08", weekday: 4, revenue: 634000, orderCount: 148, weather: "clear", note: "소금빵 16:10 품절" },
  { date: "2026-10-09", weekday: 5, revenue: 398000, orderCount: 96, weather: "clear", note: "한글날 · 연휴 귀향" },
  { date: "2026-10-10", weekday: 6, revenue: 429000, orderCount: 103, weather: "clear", note: "연휴 둘째 날" },
  { date: "2026-10-11", weekday: 0, revenue: null, orderCount: null, weather: "cloudy", note: "정기 휴무" },

  // 7주차 — 중간고사 직전 주. 이 주가 mockAnalysisNormal의 분석 대상이다
  { date: "2026-10-12", weekday: 1, revenue: 560000, orderCount: 131, weather: "cloudy", note: null },
  { date: "2026-10-13", weekday: 2, revenue: 588000, orderCount: 138, weather: "clear", note: null },
  { date: "2026-10-14", weekday: 3, revenue: 455000, orderCount: 107, weather: "rain", note: "오전부터 비" },
  { date: "2026-10-15", weekday: 4, revenue: 642000, orderCount: 150, weather: "clear", note: "소금빵 16:20 품절" },
  { date: "2026-10-16", weekday: 5, revenue: 612000, orderCount: 144, weather: "clear", note: null },
  { date: "2026-10-17", weekday: 6, revenue: 404000, orderCount: 95, weather: "cloudy", note: null },
  { date: "2026-10-18", weekday: 0, revenue: null, orderCount: null, weather: "clear", note: "정기 휴무" },
];

/** 주간 단위 총매출 (월~일 기준). 차트·검증 화면에서 추세선으로 쓴다 */
export const mockWeeklyTotals: { weekStart: string; revenue: number; note: string | null }[] = [
  { weekStart: "2026-08-31", revenue: 2915000, note: "개강주" },
  { weekStart: "2026-09-07", revenue: 2905000, note: null },
  { weekStart: "2026-09-14", revenue: 3077000, note: null },
  { weekStart: "2026-09-21", revenue: 1675000, note: "추석 연휴 · 2일 휴업" },
  { weekStart: "2026-09-28", revenue: 2968000, note: "개천절" },
  { weekStart: "2026-10-05", revenue: 3087000, note: "한글날 · 수요일 강한 비" },
  { weekStart: "2026-10-12", revenue: 3261000, note: "중간고사 직전" },
];
