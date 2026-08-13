import type { Recommendation } from "@/types";

import { generatedForecast, generatedWeeklyAnalysis } from "./generated";
import type { Mock } from "./types";

/** 이 추천들을 만든 에이전트 실행 id */
const RUN_ID = "run_20251020_0800";

/** 위 실행이 만든 추천 3건 — 우선순위 순 */
export const mockRecommendations: Mock<Recommendation>[] = [
  {
    id: "rec_20251020_stock",
    storeId: generatedWeeklyAnalysis.storeId,
    runId: RUN_ID,
    type: "inventory",
    priority: "high",
    action: "이번 주 안주 재료 발주를 평소의 70% 수준으로 줄이세요",
    description:
      "시험 기간에는 매출이 크게 줄어 재료가 남습니다. 특히 닭발과 오돌뼈는 지난주 매출의 45%를 차지했는데, 시험 주에는 이 비중이 유지되기 어렵습니다.",
    evidence: [
      {
        statement: "중간고사 기간 하루 매출은 평소의 68% 수준이었습니다",
        source: "지난 1년 중 중간고사 5일 실적",
        value: 68,
        unit: "%",
      },
      {
        statement: "이번 주 예상 매출은 492만원으로 지난주보다 182만원 적습니다",
        source: `매장 데이터 ${generatedForecast.dataSufficiency.weeksAvailable}주`,
        value: -1820000,
        unit: "원",
      },
    ],
    confidence: 0.81,
    confidenceLevel: "medium",
    actionWindow: { start: "2025-10-20", end: "2025-10-21" },
    estimatedImpact: 540000,
    status: "proposed",
    decidedAt: null,
    declineReason: null,
    linkedActionId: null,
    origin: "sample",
    createdAt: "2025-10-20T08:00:12",
    isMockData: true,
  },
  {
    id: "rec_20251020_staff",
    storeId: generatedWeeklyAnalysis.storeId,
    runId: RUN_ID,
    type: "staff",
    priority: "medium",
    action: "화요일과 수요일 아르바이트 근무를 한 명씩 줄이는 것을 검토해 보세요",
    description:
      "시험 기간 평일은 특히 조용합니다. 다만 금요일과 토요일은 시험이 끝나면서 평소만큼 바빠질 수 있으니 주말 인력은 그대로 두시는 편이 안전합니다.",
    evidence: [
      {
        statement: "시험 기간 평일 저녁 매출이 평소보다 32% 낮았습니다",
        source: "지난 1년 중 중간고사 5일 실적",
        value: -32,
        unit: "%",
      },
      {
        statement: "시험 종료 직후 금·토 매출은 평소의 137% 수준이었습니다",
        source: "지난 1년 중 중간고사 종료 직후 10일 실적",
        value: 137,
        unit: "%",
      },
    ],
    confidence: 0.64,
    confidenceLevel: "medium",
    actionWindow: { start: "2025-10-20", end: "2025-10-22" },
    estimatedImpact: 180000,
    status: "proposed",
    decidedAt: null,
    declineReason: null,
    linkedActionId: null,
    origin: "sample",
    createdAt: "2025-10-20T08:00:13",
    isMockData: true,
  },
  {
    id: "rec_20251020_promo",
    storeId: generatedWeeklyAnalysis.storeId,
    runId: RUN_ID,
    type: "marketing",
    priority: "high",
    action: "금요일(10월 24일) 오후 5시에 시험 종료 홍보를 올리세요",
    description:
      "시험이 끝나는 금요일 저녁이 이번 주의 유일한 기회입니다. 작년 같은 시기에도 시험 종료 직후 매출이 크게 올랐습니다. 홍보 문구는 STAFFI가 만들어 두겠습니다.",
    evidence: [
      {
        statement: "시험 종료 직후 기간 매출은 평소의 137% 수준이었습니다",
        source: "지난 1년 중 중간고사 종료 직후 10일 실적",
        value: 137,
        unit: "%",
      },
      {
        statement: "금요일은 이 매장에서 두 번째로 매출이 높은 요일입니다",
        source: "매장 데이터 33주",
      },
    ],
    confidence: 0.78,
    confidenceLevel: "medium",
    actionWindow: { start: "2025-10-24", end: "2025-10-24" },
    estimatedImpact: 420000,
    status: "proposed",
    decidedAt: null,
    declineReason: null,
    linkedActionId: "act_20251020_promo",
    origin: "sample",
    createdAt: "2025-10-20T08:00:14",
    isMockData: true,
  },
];
