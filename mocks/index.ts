/**
 * 목 데이터 진입점.
 * 화면은 이 파일에서만 import 하고, 나중에 API 연동 시 이 파일의 export만 교체한다.
 * 모든 export에는 isMockData: true가 들어 있어 "예시 데이터" 배지를 자동으로 띄울 수 있다.
 */

import type { DashboardData } from "@/types";
import { mockContentGeneration } from "./content";
import { mockForecastConfident, mockForecastInsufficient } from "./forecast";
import { mockMissedOpportunities } from "./missed-opportunity";
import { mockStore, mockStoreNew } from "./store";
import type { Mock } from "./types";
import { mockValidationMissed } from "./verification";
import { mockAnalysisNormal } from "./weekly-analysis";

export * from "./academic-calendar";
export * from "./agent";
export * from "./recommendation";
export * from "./content";
export * from "./daily-sales";
export * from "./forecast";
export * from "./missed-opportunity";
export * from "./store";
export * from "./types";
export * from "./upload";
export * from "./verification";
export * from "./weekly-analysis";

/** 정상 시나리오 대시보드 — 데이터 충분, 예측 신뢰도 높음 */
export const mockDashboardData: Mock<DashboardData> = {
  store: mockStore,
  weeklyAnalysis: mockAnalysisNormal,
  forecast: mockForecastConfident,
  missedOpportunities: mockMissedOpportunities,
  verification: mockValidationMissed,
  isMockData: true,
};

/** 데이터 부족 시나리오 대시보드 — 예측 대신 안내 문구, 검증 이력 없음 */
export const mockDashboardDataInsufficient: Mock<DashboardData> = {
  store: mockStoreNew,
  weeklyAnalysis: {
    ...mockAnalysisNormal,
    storeId: mockStoreNew.id,
    period: { start: "2026-10-12", end: "2026-10-18" },
    totalRevenue: 1284000,
    changeRateVsPrevWeek: 11.2,
    prevWeekRevenue: 1154000,
    topMenus: mockAnalysisNormal.topMenus.slice(0, 5).map((m) => ({
      ...m,
      quantity: Math.round(m.quantity * 0.39),
      revenue: Math.round((m.revenue * 0.39) / 500) * 500,
    })),
  },
  forecast: mockForecastInsufficient,
  missedOpportunities: [],
  verification: null,
  isMockData: true,
};

/** 콘텐츠 생성 시연용 기본값 */
export const mockContent = mockContentGeneration;
