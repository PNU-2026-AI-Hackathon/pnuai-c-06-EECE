import type { EarlySalesEnd } from "@/types";

import type { Mock } from "./types";

/**
 * 대표 시나리오 — 3주 연속 목요일 소금빵 판매 조기 종료.
 * 시스템은 "품절"이라고 단정하지 않고 후보만 제시하며, 확정은 사장님이 한다.
 */
export const mockEarlySalesEnd: Mock<EarlySalesEnd> = {
  id: "ese_20261015_saltbread",
  storeId: "store_pnu_001",
  date: "2026-10-15",
  menuName: "소금빵",
  lastSoldAt: "16:20",
  usualClosingAt: "22:00",
  earlierByMinutes: 340,
  opportunityRange: { low: 63000, high: 87500 },
  repeatedWeeks: 3,
  possibleCauses: ["sold_out", "stopped_selling", "no_demand"],
  reasoning:
    "목요일 16시 20분 이후 소금빵 결제가 0건인데, 다른 목요일 같은 시간대에는 평균 18~25개가 더 팔렸습니다. 3주 연속 같은 패턴이라 우연으로 보기는 어렵습니다.",
  confidence: "high",
  ownerConfirmation: "unconfirmed",
  ownerNote: null,
  origin: "sample",
  isMockData: true,
};

/** 같은 패턴의 직전 2주치 — 사장님이 이미 확인해 준 기록 */
export const mockEarlySalesEndHistory: Mock<EarlySalesEnd>[] = [
  {
    id: "ese_20261008_saltbread",
    storeId: "store_pnu_001",
    date: "2026-10-08",
    menuName: "소금빵",
    lastSoldAt: "16:10",
    usualClosingAt: "22:00",
    earlierByMinutes: 350,
    opportunityRange: { low: 70000, high: 94500 },
    repeatedWeeks: 2,
    possibleCauses: ["sold_out", "no_demand"],
    reasoning:
      "16시 10분 이후 소금빵 결제가 끊겼고, 함께 주문되던 아이스 아메리카노도 같은 시간대에 12% 줄었습니다.",
    confidence: "high",
    ownerConfirmation: "confirmed_sold_out",
    ownerNote: null,
    origin: "sample",
    isMockData: true,
  },
  {
    id: "ese_20261001_saltbread",
    storeId: "store_pnu_001",
    date: "2026-10-01",
    menuName: "소금빵",
    lastSoldAt: "16:40",
    usualClosingAt: "22:00",
    earlierByMinutes: 320,
    opportunityRange: { low: 52500, high: 73500 },
    repeatedWeeks: 1,
    possibleCauses: ["sold_out", "no_demand", "pos_missing"],
    reasoning: "16시 40분 이후 소금빵 결제가 0건입니다. 평소 목요일 저녁에는 15~21개가 더 팔렸습니다.",
    confidence: "medium",
    ownerConfirmation: "confirmed_sold_out",
    ownerNote: null,
    origin: "sample",
    isMockData: true,
  },
];

/** 사장님이 "다른 이유였다"고 답한 케이스 — 이런 기록이 다음 탐지를 고친다 */
export const mockEarlySalesEndOther: Mock<EarlySalesEnd> = {
  id: "ese_20261016_croffle",
  storeId: "store_pnu_001",
  date: "2026-10-16",
  menuName: "크로플",
  lastSoldAt: "19:05",
  usualClosingAt: "22:00",
  earlierByMinutes: 175,
  opportunityRange: { low: 16500, high: 22000 },
  repeatedWeeks: 1,
  possibleCauses: ["no_demand", "stopped_selling", "early_closing"],
  reasoning:
    "19시 이후 크로플 결제가 없습니다. 다만 금요일 저녁은 원래 주문이 적어 판매 종료인지 수요 감소인지 단정하기 어렵습니다.",
  confidence: "low",
  ownerConfirmation: "other_reason",
  ownerNote: "그날 기계 청소하느라 8시에 크로플만 먼저 내렸어요",
  origin: "sample",
  isMockData: true,
};

/** 화면에 그대로 넣을 목록 (확인 안 된 것부터) */
export const mockEarlySalesEnds: Mock<EarlySalesEnd>[] = [
  mockEarlySalesEnd,
  mockEarlySalesEndOther,
  ...mockEarlySalesEndHistory,
];
