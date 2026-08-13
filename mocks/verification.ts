import type { ForecastVerification } from "@/types";
import type { Mock } from "./types";

/**
 * 예측이 빗나간 주 — 2026-10-05~10-11.
 * +18%를 예측했지만 실제는 +4%였고, 강수와 한글날 연휴를 반영하지 못한 것이 원인이다.
 * "틀린 것을 숨기지 않는다"를 보여주는 핵심 시연 데이터.
 */
export const mockValidationMissed: Mock<ForecastVerification> = {
  storeId: "store_pnu_001",
  period: { start: "2026-10-05", end: "2026-10-11" },
  predictedChangeRate: 18,
  actualChangeRate: 4,
  errorPoints: -14,
  predictedConfidence: "medium",
  errorAnalysis:
    "수요일(10월 7일) 오후에 내린 강한 비로 그날 매출이 예상보다 13만원 낮았고, 금요일 한글날 연휴로 학생들이 빠져나가 금·토 매출이 예상의 68%에 그쳤습니다. 예측 당시 강수 예보와 연휴 유출을 반영하지 않은 것이 오차의 대부분입니다.",
  reflectedInModel: true,
  reflectionNote: "강수 확률과 공휴일 직전·직후 유출을 예측 변수에 추가했습니다. 다음 주 예측부터 적용됩니다.",
  origin: "sample",
  isMockData: true,
};

/** 예측이 잘 맞은 주 — 검증 화면에서 비교용으로 함께 보여준다 */
export const mockValidationHit: Mock<ForecastVerification> = {
  storeId: "store_pnu_001",
  period: { start: "2026-09-28", end: "2026-10-04" },
  predictedChangeRate: 74,
  actualChangeRate: 77.2,
  errorPoints: 3.2,
  predictedConfidence: "high",
  errorAnalysis:
    "추석 휴업이 있던 전주 대비 회복을 예측한 것이라 방향과 크기가 모두 맞았습니다. 개천절로 토요일이 낮았던 부분까지 예측에 들어가 있었습니다.",
  reflectedInModel: false,
  reflectionNote: null,
  origin: "sample",
  isMockData: true,
};

/** 검증 이력 목록 (최신순) */
export const mockVerifications: Mock<ForecastVerification>[] = [
  mockValidationMissed,
  mockValidationHit,
];
