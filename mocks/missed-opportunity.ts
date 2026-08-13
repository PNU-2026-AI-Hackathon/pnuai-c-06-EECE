import type { MissedOpportunity } from "@/types";
import type { Mock } from "./types";

/**
 * 대표 시나리오 — 3주 연속 목요일 소금빵 품절.
 * 매주 같은 요일에 같은 메뉴가 마감 5~6시간 전에 떨어지고 있다.
 */
export const mockMissedOpportunity: Mock<MissedOpportunity> = {
  id: "miss_20261015_saltbread",
  storeId: "store_pnu_001",
  date: "2026-10-15",
  menuName: "소금빵",
  estimatedSoldOutAt: "16:20",
  usualClosingAt: "22:00",
  estimatedOpportunity: 87500,
  repeatedWeeks: 3,
  reasoning:
    "목요일 16시 20분 이후 소금빵 결제가 0건인데, 다른 목요일 같은 시간대에는 평균 25개가 더 팔렸습니다. 3주 연속 같은 패턴이라 우연으로 보기 어렵습니다.",
  confidence: "high",
  origin: "sample",
  isMockData: true,
};

/** 같은 패턴의 직전 2주치 — "3주 연속"의 근거가 되는 기록 */
export const mockMissedOpportunityHistory: Mock<MissedOpportunity>[] = [
  {
    id: "miss_20261008_saltbread",
    storeId: "store_pnu_001",
    date: "2026-10-08",
    menuName: "소금빵",
    estimatedSoldOutAt: "16:10",
    usualClosingAt: "22:00",
    estimatedOpportunity: 94500,
    repeatedWeeks: 2,
    reasoning:
      "16시 10분 이후 소금빵 결제가 끊겼고, 함께 주문되던 아이스 아메리카노도 같은 시간대에 12% 줄었습니다.",
    confidence: "high",
    origin: "sample",
    isMockData: true,
  },
  {
    id: "miss_20261001_saltbread",
    storeId: "store_pnu_001",
    date: "2026-10-01",
    menuName: "소금빵",
    estimatedSoldOutAt: "16:40",
    usualClosingAt: "22:00",
    estimatedOpportunity: 73500,
    repeatedWeeks: 1,
    reasoning: "16시 40분 이후 소금빵 결제가 0건입니다. 평소 목요일 저녁에는 21개가 더 팔렸습니다.",
    confidence: "medium",
    origin: "sample",
    isMockData: true,
  },
];

/** 다른 메뉴에서 한 번만 발생한 케이스 — 반복이 아니라 판단을 보류하는 예시 */
export const mockMissedOpportunityOnce: Mock<MissedOpportunity> = {
  id: "miss_20261016_croffle",
  storeId: "store_pnu_001",
  date: "2026-10-16",
  menuName: "크로플",
  estimatedSoldOutAt: "19:05",
  usualClosingAt: "22:00",
  estimatedOpportunity: 22000,
  repeatedWeeks: 1,
  reasoning:
    "19시 이후 크로플 결제가 없습니다. 다만 금요일 저녁은 원래 주문이 적어 품절인지 수요 감소인지 단정하기 어렵습니다.",
  confidence: "low",
  origin: "sample",
  isMockData: true,
};

/** 놓친 기회 화면에 그대로 넣을 목록 (최신순) */
export const mockMissedOpportunities: Mock<MissedOpportunity>[] = [
  mockMissedOpportunity,
  mockMissedOpportunityOnce,
  ...mockMissedOpportunityHistory,
];
