import type { HourlySales, MenuSales, WeeklyAnalysis, WeekdaySales } from "@/types";
import type { Mock } from "./types";

/** 2026-10-12 ~ 10-18 메뉴별 판매 실적 (총 3,261,000원 기준) */
export const mockTopMenus: MenuSales[] = [
  { menuName: "아이스 아메리카노", quantity: 318, revenue: 1272000, share: 39.0 },
  { menuName: "카페라떼", quantity: 141, revenue: 634500, share: 19.5 },
  { menuName: "바닐라라떼", quantity: 78, revenue: 390000, share: 12.0 },
  { menuName: "소금빵", quantity: 96, revenue: 336000, share: 10.3 },
  { menuName: "아이스티", quantity: 62, revenue: 217000, share: 6.7 },
  { menuName: "크로플", quantity: 31, revenue: 170500, share: 5.2 },
  { menuName: "딸기라떼", quantity: 22, revenue: 121000, share: 3.7 },
  { menuName: "자몽에이드", quantity: 24, revenue: 120000, share: 3.6 },
];

/** 요일별 매출 — 일요일은 정기 휴무라 0이다 */
export const mockWeekdaySales: WeekdaySales[] = [
  { weekday: 0, revenue: 0, orderCount: 0 },
  { weekday: 1, revenue: 560000, orderCount: 131 },
  { weekday: 2, revenue: 588000, orderCount: 138 },
  { weekday: 3, revenue: 455000, orderCount: 107 },
  { weekday: 4, revenue: 642000, orderCount: 150 },
  { weekday: 5, revenue: 612000, orderCount: 144 },
  { weekday: 6, revenue: 404000, orderCount: 95 },
];

/** 시간대별 매출 — 점심(12~13시)과 오후 공강 시간대에 몰린다 */
export const mockHourlySales: HourlySales[] = [
  { hour: 8, revenue: 96000, orderCount: 24 },
  { hour: 9, revenue: 148000, orderCount: 36 },
  { hour: 10, revenue: 214000, orderCount: 52 },
  { hour: 11, revenue: 268000, orderCount: 63 },
  { hour: 12, revenue: 402000, orderCount: 92 },
  { hour: 13, revenue: 488000, orderCount: 112 },
  { hour: 14, revenue: 331000, orderCount: 78 },
  { hour: 15, revenue: 289000, orderCount: 68 },
  { hour: 16, revenue: 262000, orderCount: 62 },
  { hour: 17, revenue: 196000, orderCount: 46 },
  { hour: 18, revenue: 152000, orderCount: 36 },
  { hour: 19, revenue: 168000, orderCount: 39 },
  { hour: 20, revenue: 158000, orderCount: 37 },
  { hour: 21, revenue: 89000, orderCount: 20 },
];

/**
 * 정상 시나리오 — 중간고사 직전 주(2026-10-12~10-18)의 주간 분석.
 * 전주는 한글날과 강한 비가 겹쳐 낮았기 때문에 증감률을 볼 때 주의가 필요하다.
 */
export const mockAnalysisNormal: Mock<WeeklyAnalysis> = {
  storeId: "store_pnu_001",
  period: { start: "2026-10-12", end: "2026-10-18" },
  totalRevenue: 3261000,
  changeRateVsPrevWeek: 5.6,
  prevWeekRevenue: 3087000,
  topMenus: mockTopMenus,
  weekdaySales: mockWeekdaySales,
  hourlySales: mockHourlySales,
  origin: "sample",
  isMockData: true,
};

/** 비교용 이전 주(2026-10-05~10-11) — 한글날·강한 비로 눌린 주 */
export const mockAnalysisPrevWeek: Mock<WeeklyAnalysis> = {
  storeId: "store_pnu_001",
  period: { start: "2026-10-05", end: "2026-10-11" },
  totalRevenue: 3087000,
  changeRateVsPrevWeek: 4.0,
  prevWeekRevenue: 2968000,
  topMenus: [
    { menuName: "아이스 아메리카노", quantity: 296, revenue: 1184000, share: 38.4 },
    { menuName: "카페라떼", quantity: 138, revenue: 621000, share: 20.1 },
    { menuName: "바닐라라떼", quantity: 71, revenue: 355000, share: 11.5 },
    { menuName: "소금빵", quantity: 89, revenue: 311500, share: 10.1 },
    { menuName: "아이스티", quantity: 58, revenue: 203000, share: 6.6 },
    { menuName: "크로플", quantity: 29, revenue: 159500, share: 5.2 },
    { menuName: "자몽에이드", quantity: 26, revenue: 130000, share: 4.2 },
    { menuName: "딸기라떼", quantity: 22, revenue: 121000, share: 3.9 },
  ],
  weekdaySales: [
    { weekday: 0, revenue: 0, orderCount: 0 },
    { weekday: 1, revenue: 578000, orderCount: 136 },
    { weekday: 2, revenue: 596000, orderCount: 140 },
    { weekday: 3, revenue: 452000, orderCount: 109 },
    { weekday: 4, revenue: 634000, orderCount: 148 },
    { weekday: 5, revenue: 398000, orderCount: 96 },
    { weekday: 6, revenue: 429000, orderCount: 103 },
  ],
  hourlySales: mockHourlySales.map((h) => ({
    ...h,
    revenue: Math.round((h.revenue * 3087000) / 3261000 / 1000) * 1000,
    orderCount: Math.round((h.orderCount * 3087000) / 3261000),
  })),
  origin: "sample",
  isMockData: true,
};
