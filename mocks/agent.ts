import type {
  AgentAction,
  AgentHealth,
  AgentNotification,
  AgentPolicy,
  AgentRun,
  DataFreshness,
} from "@/types";

import { generatedWeeklyAnalysis } from "./generated";
import type { Mock } from "./types";

/**
 * 에이전트 실행 예시 — 2025-10-20(월) 아침 정기 점검.
 * 술집 CSV에서 계산된 실제 수치(674만원, -27%)를 그대로 인용한다.
 */
export const mockAgentRun: Mock<AgentRun> = {
  id: "run_20251020_0800",
  storeId: generatedWeeklyAnalysis.storeId,
  trigger: {
    kind: "schedule",
    description: "매주 월요일 아침 정기 점검",
    scheduledFor: "2025-10-20T08:00:00",
  },
  status: "succeeded",
  startedAt: "2025-10-20T08:00:02",
  finishedAt: "2025-10-20T08:00:19",
  steps: [
    {
      order: 1,
      tool: "check_data_freshness",
      label: "데이터 상태 확인",
      status: "succeeded",
      startedAt: "2025-10-20T08:00:02",
      durationMs: 340,
      summary: "마지막 매출 데이터는 어제(10월 19일)까지입니다.",
      reason: null,
    },
    {
      order: 2,
      tool: "analyze_weekly",
      label: "지난주 매출 정리",
      status: "succeeded",
      startedAt: "2025-10-20T08:00:03",
      durationMs: 1210,
      summary: "지난주 674만원, 전주 대비 +2.1%였습니다.",
      reason: null,
    },
    {
      order: 3,
      tool: "verify_last_forecast",
      label: "지난 예측 검증",
      status: "succeeded",
      startedAt: "2025-10-20T08:00:04",
      durationMs: 890,
      summary: "지난주 예측 +7.5%, 실제 +13.9%로 6.4%p 빗나갔습니다.",
      reason: null,
    },
    {
      order: 4,
      tool: "get_academic_events",
      label: "학사일정 확인",
      status: "succeeded",
      startedAt: "2025-10-20T08:00:05",
      durationMs: 210,
      summary: "오늘부터 10월 24일까지 부산대 중간고사입니다.",
      reason: null,
    },
    {
      order: 5,
      tool: "forecast_next_week",
      label: "이번 주 수요 예측",
      status: "succeeded",
      startedAt: "2025-10-20T08:00:06",
      durationMs: 2380,
      summary: "이번 주 매출은 27% 감소, 약 492만원으로 예상됩니다.",
      reason: null,
    },
    {
      order: 6,
      tool: "detect_missed_opportunity",
      label: "놓친 판매 기회 확인",
      status: "skipped",
      startedAt: "2025-10-20T08:00:09",
      durationMs: 60,
      summary: "판단할 수 없어 건너뛰었습니다.",
      reason: "일별 집계 파일이라 결제 시각과 품절 정보가 없습니다.",
    },
    {
      order: 7,
      tool: "send_notification",
      label: "사장님께 알림",
      status: "succeeded",
      startedAt: "2025-10-20T08:00:18",
      durationMs: 640,
      summary: "카카오톡으로 요약과 추천 3건을 보냈습니다.",
      reason: null,
    },
  ],
  headline: "이번 주는 중간고사입니다. 매출이 27% 줄어들 것으로 봅니다.",
  recommendationIds: ["rec_20251020_stock", "rec_20251020_staff", "rec_20251020_promo"],
  notified: true,
  skipReason: null,
  error: null,
  origin: "sample",
  isMockData: true,
};

/** 홍보 추천에 딸린 실행 행동 — 승인 전에는 게시하지 않는다 */
export const mockAgentAction: Mock<AgentAction> = {
  id: "act_20251020_promo",
  recommendationId: "rec_20251020_promo",
  kind: "draft_content",
  title: "홍보 문구 만들기",
  preview:
    "시험 끝나고 오는 금요일 🍻\n중간고사 수고하셨습니다. 금요일 저녁, 자리 넉넉히 비워두겠습니다.\n#부산대 #장전동술집 #시험끝",
  requiresApproval: true,
  reversible: true,
  executeBy: "2025-10-24T17:00:00",
  status: "pending_approval",
  executedAt: null,
  resultSummary: null,
  isMockData: true,
};

/** 사장님에게 나간 알림 */
export const mockAgentNotification: Mock<AgentNotification> = {
  id: "noti_20251020_0800",
  runId: mockAgentRun.id,
  channel: "kakao",
  title: "이번 주는 중간고사입니다",
  body: "매출이 27% 줄어들 것으로 봅니다. 재료 발주와 금요일 홍보, 두 가지만 확인해 주세요.",
  sentAt: "2025-10-20T08:00:19",
  readAt: "2025-10-20T09:12:44",
  deepLink: "/",
  isMockData: true,
};

/** 데이터 신선도 — 어제까지 데이터가 있으므로 정상 */
export const mockDataFreshness: Mock<DataFreshness> = {
  lastDataDate: "2025-10-19",
  daysSinceLastData: 1,
  level: "fresh",
  message: "어제까지의 매출이 반영되어 있습니다.",
  blocksForecast: false,
  isMockData: true,
};

/** 데이터가 오래된 경우 — 예측을 멈추고 새 파일을 요청한다 */
export const mockDataFreshnessStale: Mock<DataFreshness> = {
  lastDataDate: "2025-09-07",
  daysSinceLastData: 43,
  level: "stale",
  message:
    "마지막 매출 파일이 6주 지났습니다. 지금 예측하면 오래된 기준으로 계산하게 되어, 새 파일을 올려주실 때까지 예측을 멈춰 두었습니다.",
  blocksForecast: true,
  isMockData: true,
};

/** 에이전트 설정 — 기본값은 승인 후 실행(L2) */
export const mockAgentPolicy: Mock<AgentPolicy> = {
  storeId: generatedWeeklyAnalysis.storeId,
  autonomyLevel: "recommend_with_approval",
  schedule: "0 8 * * 1",
  channels: ["kakao"],
  quietHours: { start: "22:00", end: "09:00" },
  changeRateThreshold: 10,
  repeatWeeksThreshold: 2,
  isMockData: true,
};

/** 에이전트 성적표 — 스스로를 평가한 누적 기록 */
export const mockAgentHealth: Mock<AgentHealth> = {
  storeId: generatedWeeklyAnalysis.storeId,
  since: "2025-08-25",
  runCount: 8,
  verifiedForecastCount: 7,
  avgAbsErrorPoints: 6.2,
  recommendationCount: 21,
  acceptedRate: 0.62,
  topDeclineReason: "already_doing",
  origin: "sample",
  isMockData: true,
};
