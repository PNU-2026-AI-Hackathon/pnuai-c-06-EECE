/**
 * 행동 추천 계약.
 * STAFFI의 핵심은 예측이 아니라 "그래서 지금 무엇을 해야 하는가"이므로,
 * 추천은 분석 결과와 같은 급의 1급 데이터로 다룬다.
 */

import type { ConfidenceLevel, DataOrigin, DateRange, ISODate, ISODateTime, Won } from "./index";

/** 추천이 건드리는 영역 — 사장님이 실제로 하는 일 단위로 나눈다 */
export type RecommendationType =
  /** 재료·준비 등 매장 운영 */
  | "operation"
  /** 직원 배치·근무 시간 */
  | "staff"
  /** 홍보·콘텐츠 */
  | "marketing"
  /** 발주·재고 */
  | "inventory"
  /** 데이터 자체에 대한 요청 (파일 업로드 등) */
  | "data";

/** 추천 우선순위 — 색이 아니라 이 값과 라벨로 구분한다 */
export type RecommendationPriority = "high" | "medium" | "low";

/**
 * 사장님이 추천에 대해 내린 결정.
 * declined의 이유는 다음 추천을 고치는 학습 신호로 쓴다.
 */
export type RecommendationStatus =
  /** 아직 보지 않았거나 결정하지 않음 */
  | "proposed"
  /** 하겠다고 함 */
  | "accepted"
  /** 하지 않겠다고 함 */
  | "declined"
  /** 실제로 실행 완료 */
  | "done"
  /** 실행 시점이 지나버림 */
  | "expired";

/** 추천을 뒷받침하는 근거 한 줄 — 반드시 출처를 함께 둔다 */
export interface EvidenceStatement {
  /** 사장님이 읽을 문장 (예: "최근 3회 시험 종료 후 금요일 매출 평균 +17.8%") */
  statement: string;
  /** 이 문장이 어디서 나왔는지 (예: "매장 데이터 33주", "부산대 학사일정") */
  source: string;
  /** 관련 수치 — 화면에서 강조하고 싶을 때만 */
  value?: number;
  /** value의 단위 ("%", "원", "건") */
  unit?: string;
}

/**
 * 행동 추천 한 건.
 * 근거 없는 추천은 만들지 않는다 (evidence는 최소 1개).
 */
export interface Recommendation {
  /** 추천 고유 식별자 */
  id: string;
  /** 대상 매장 id */
  storeId: string;
  /** 이 추천을 만든 에이전트 실행 id */
  runId: string;
  /** 추천 영역 */
  type: RecommendationType;
  /** 우선순위 */
  priority: RecommendationPriority;
  /** 한 줄 행동 문장, 명령형 (예: "목요일 소금빵 반죽을 20개 더 준비하세요") */
  action: string;
  /** 왜 해야 하는지 설명 (2~3문장) */
  description: string;
  /** 근거 목록 — 최소 1개 */
  evidence: EvidenceStatement[];
  /** 이 추천의 확신 정도 (0~1). 화면에는 등급으로 환산해 보여준다 */
  confidence: number;
  /** 확신 등급 — confidence를 사장님 언어로 바꾼 값 */
  confidenceLevel: ConfidenceLevel;
  /** 언제까지 하면 되는지 */
  actionWindow: DateRange;
  /** 실행하지 않으면 놓치는 추정 금액 — 계산할 수 없으면 null */
  estimatedImpact: Won | null;
  /** 현재 상태 */
  status: RecommendationStatus;
  /** 사장님이 결정한 시각 — 아직 결정 전이면 null */
  decidedAt: ISODateTime | null;
  /** 거절 사유 (선택지 또는 자유 입력) — 다음 추천 개선에 쓴다 */
  declineReason: string | null;
  /** 이 추천을 실행하려면 STAFFI가 대신 할 수 있는 일이 있는지 */
  linkedActionId: string | null;
  /** 실제 데이터 기반인지 예시인지 */
  origin: DataOrigin;
  /** 생성 시각 */
  createdAt: ISODateTime;
}

/** 사장님이 거절할 때 고를 수 있는 정형 사유 — 자유 입력보다 학습에 유용하다 */
export type DeclineReasonCode =
  | "already_doing"
  | "not_applicable"
  | "no_time"
  | "too_expensive"
  | "disagree_with_data"
  | "other";

/** STAFFI가 사장님 대신 할 수 있는 일의 종류 */
export type AgentActionKind =
  /** 홍보 문구·릴스 대본 초안 만들기 */
  | "draft_content"
  /** 정해진 시각에 게시 예약 */
  | "schedule_post"
  /** 발주서 초안 만들기 */
  | "draft_order"
  /** 직원에게 공지 보내기 */
  | "notify_staff";

/** 실행 상태 — 승인 전에는 절대 executed로 가지 않는다 */
export type AgentActionStatus =
  | "pending_approval"
  | "approved"
  | "executed"
  | "rejected"
  | "failed";

/**
 * 추천에 딸린 실행 가능한 행동.
 * 돈이 나가거나 외부에 노출되는 행동은 requiresApproval이 항상 true여야 한다.
 */
export interface AgentAction {
  /** 행동 고유 식별자 */
  id: string;
  /** 어떤 추천에서 나온 행동인지 */
  recommendationId: string;
  /** 행동 종류 */
  kind: AgentActionKind;
  /** 버튼에 쓸 짧은 이름 (예: "홍보 문구 만들기") */
  title: string;
  /** 승인 전에 사장님이 확인할 미리보기 (게시글 초안 등) */
  preview: string | null;
  /** 사장님 승인이 필요한지 — 외부 노출·비용 발생 행동은 반드시 true */
  requiresApproval: boolean;
  /** 실행 후 되돌릴 수 있는지 */
  reversible: boolean;
  /** 이 시각까지 실행해야 의미가 있음 */
  executeBy: ISODateTime | null;
  /** 현재 상태 */
  status: AgentActionStatus;
  /** 실제 실행 시각 — 아직이면 null */
  executedAt: ISODateTime | null;
  /** 실행 결과 한 줄 — 실패 시 사유 */
  resultSummary: string | null;
}

/**
 * 데이터 신선도.
 * 마지막 데이터가 오래되면 예측을 멈추고 새 파일을 요청한다 (원칙 2).
 */
export interface DataFreshness {
  /** 확보된 마지막 매출 데이터 날짜 */
  lastDataDate: ISODate;
  /** 오늘 기준 경과 일수 */
  daysSinceLastData: number;
  /** fresh: 2주 이내 · aging: 3~4주 · stale: 5주 이상 */
  level: "fresh" | "aging" | "stale";
  /** 사장님에게 보여줄 안내 문장 */
  message: string;
  /** true면 예측을 표시하지 않고 이 안내로 대체한다 */
  blocksForecast: boolean;
}
