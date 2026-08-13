import type { Forecast, ForecastEvidence } from "@/types";
import { mockEventsForTargetWeek } from "./academic-calendar";
import type { Mock } from "./types";

/**
 * 예측 근거 — contribution의 합(+9 +5 -3 +2 = +13)이 expectedChangeRate와 일치한다.
 * 화면에서는 수치 옆에 이 목록이 항상 함께 표시된다.
 */
export const mockForecastEvidence: ForecastEvidence[] = [
  {
    label: "중간고사 기간 체류시간 증가",
    contribution: 9,
    source: "매장 데이터 12주 · 부산대 학사일정",
    detail: "지난 두 학기 시험 기간에 오후 2~6시 매출이 평균 21% 늘었습니다.",
  },
  {
    label: "시험 기간 아메리카노 재구매 패턴",
    contribution: 5,
    source: "매장 데이터 33주",
    detail: "시험 주에는 같은 손님이 하루 2회 이상 방문하는 비율이 8%에서 14%로 올랐습니다.",
  },
  {
    label: "수요일 강수 예보",
    contribution: -3,
    source: "기상청 중기예보 (10월 21일 비)",
    detail: "비 오는 평일은 평균 18% 낮았습니다.",
  },
  {
    label: "시험 마지막 날 이후 이탈",
    contribution: 2,
    source: "매장 데이터 12주",
    detail: "시험이 토요일에 끝나 주말 매출 감소폭이 평소보다 작습니다.",
  },
];

/**
 * 데이터가 충분하고 신뢰도가 높은 예측 — 중간고사 주(2026-10-19~10-25).
 */
export const mockForecastConfident: Mock<Forecast> = {
  storeId: "store_pnu_001",
  targetWeek: { start: "2026-10-19", end: "2026-10-25" },
  targetWeekLabel: "2026년 10월 4주차 (중간고사)",
  expectedChangeRate: 13,
  confidence: "high",
  evidence: mockForecastEvidence,
  academicEvents: mockEventsForTargetWeek,
  dataSufficiency: {
    level: "sufficient",
    message: "33주치 매출과 지난 두 학기 시험 기간 기록이 있어 예측을 신뢰할 수 있습니다.",
    weeksAvailable: 33,
    weeksRequired: 8,
  },
  origin: "sample",
  isMockData: true,
};

/**
 * 데이터 부족 시나리오 — 개업 3주차 매장.
 * 추측하지 않고 예측 대신 dataSufficiency.message를 그대로 보여준다.
 */
export const mockForecastInsufficient: Mock<Forecast> = {
  storeId: "store_pnu_002",
  targetWeek: { start: "2026-10-19", end: "2026-10-25" },
  targetWeekLabel: "2026년 10월 4주차 (중간고사)",
  expectedChangeRate: null,
  confidence: null,
  evidence: [],
  academicEvents: mockEventsForTargetWeek,
  dataSufficiency: {
    level: "insufficient",
    message:
      "매출 데이터가 3주치뿐이라 다음 주 예측을 만들 수 없습니다. 5주치가 더 쌓이면 예측을 시작합니다. 그때까지는 학사일정만 안내해 드릴게요.",
    weeksAvailable: 3,
    weeksRequired: 8,
  },
  origin: "sample",
  isMockData: true,
};

/**
 * 중간 단계 시나리오 — 데이터는 있지만 시험 기간 이력이 한 번뿐이라 신뢰도가 낮다.
 */
export const mockForecastLimited: Mock<Forecast> = {
  storeId: "store_pnu_001",
  targetWeek: { start: "2026-11-02", end: "2026-11-08" },
  targetWeekLabel: "2026년 11월 1주차 (대학축제)",
  expectedChangeRate: 6,
  confidence: "low",
  evidence: [
    {
      label: "축제 기간 유동인구 증가",
      contribution: 11,
      source: "부산대 학사일정 · 상권 카페 6곳 표본",
      detail: "축제 3일간 캠퍼스 유동인구가 평소의 1.7배였습니다.",
    },
    {
      label: "축제 중 주점·푸드트럭으로 수요 이동",
      contribution: -5,
      source: "매장 데이터 1회 (2025년 축제)",
      detail: "작년 축제 때 저녁 시간대 카페 매출은 오히려 22% 줄었습니다.",
    },
  ],
  academicEvents: [
    { name: "대학축제 (효원대동제)", startDate: "2026-11-04", endDate: "2026-11-06", type: "festival" },
  ],
  dataSufficiency: {
    level: "limited",
    message: "축제 기간 데이터가 작년 한 번뿐이라 오차가 클 수 있습니다. 참고용으로만 봐주세요.",
    weeksAvailable: 33,
    weeksRequired: 8,
  },
  origin: "sample",
  isMockData: true,
};
