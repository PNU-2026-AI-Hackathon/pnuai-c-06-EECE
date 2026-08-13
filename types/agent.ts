/**
 * 에이전트 계약.
 * STAFFI는 사장님이 열어봐야 도는 화면이 아니라, 스스로 돌고 먼저 알리는 AI 직원이다.
 * 여기 있는 타입은 "언제 돌았고, 무엇을 했고, 무엇을 근거로 판단했는지"를 남기기 위한 것이다.
 */

import type { DataOrigin, ISODate, ISODateTime } from "./index";

/** 에이전트를 깨우는 계기 */
export type AgentTriggerKind =
  /** 정해진 시각 (예: 매주 월요일 08:00) */
  | "schedule"
  /** 새 매출 데이터가 들어옴 */
  | "data_arrived"
  /** 학사일정이 다가옴 (예: 시험 종료 D-3) */
  | "calendar"
  /** 사장님이 직접 실행 */
  | "manual";

/** 이번 실행이 왜 시작됐는지 */
export interface AgentTrigger {
  /** 계기 종류 */
  kind: AgentTriggerKind;
  /** 사장님에게 보여줄 설명 (예: "매주 월요일 아침 정기 점검") */
  description: string;
  /** 예정 시각 — schedule일 때만 */
  scheduledFor?: ISODateTime;
}

/**
 * 에이전트가 쓸 수 있는 도구 목록 (화이트리스트).
 * 통계 계산은 전부 이 도구들이 하고, LLM은 결과를 해석만 한다.
 * 목록에 없는 일은 하지 않는다.
 */
export type AgentToolName =
  /** 주간 매출 집계 */
  | "analyze_weekly"
  /** 다음 주 수요 예측 */
  | "forecast_next_week"
  /** 지난 예측과 실제 비교 */
  | "verify_last_forecast"
  /** 품절로 인한 판매 기회 추정 */
  | "detect_missed_opportunity"
  /** 학사일정 조회 */
  | "get_academic_events"
  /** 데이터 신선도 확인 */
  | "check_data_freshness"
  /** 홍보 문구·릴스 대본 생성 */
  | "generate_content"
  /** 사장님에게 알림 발송 */
  | "send_notification";

/** 실행 단계 하나의 결과 */
export type AgentStepStatus = "succeeded" | "failed" | "skipped";

/** 에이전트가 밟은 단계 한 개 — 활동 타임라인에 그대로 표시된다 */
export interface AgentStep {
  /** 실행 순서 (1부터) */
  order: number;
  /** 사용한 도구 */
  tool: AgentToolName;
  /** 사장님이 읽을 단계 이름 (예: "지난주 매출 정리") */
  label: string;
  /** 단계 결과 */
  status: AgentStepStatus;
  /** 시작 시각 */
  startedAt: ISODateTime;
  /** 걸린 시간 (밀리초) */
  durationMs: number;
  /** 이 단계에서 알아낸 것 한 줄 (예: "지난주 674만원, 전주 대비 +2.1%") */
  summary: string;
  /** 건너뛰거나 실패한 이유 — 정상 완료면 null */
  reason: string | null;
}

/** 실행 전체의 상태 */
export type AgentRunStatus = "running" | "succeeded" | "failed" | "skipped";

/**
 * 에이전트 실행 1회 기록.
 * 사장님 화면의 "STAFFI가 한 일" 타임라인이자, 문제가 생겼을 때의 감사 로그다.
 */
export interface AgentRun {
  /** 실행 고유 식별자 */
  id: string;
  /** 대상 매장 id */
  storeId: string;
  /** 이번 실행의 계기 */
  trigger: AgentTrigger;
  /** 실행 상태 */
  status: AgentRunStatus;
  /** 시작 시각 */
  startedAt: ISODateTime;
  /** 종료 시각 — 진행 중이면 null */
  finishedAt: ISODateTime | null;
  /** 밟은 단계들 (순서대로) */
  steps: AgentStep[];
  /** 이번 실행에서 발견한 핵심 한 문장 (없으면 null) */
  headline: string | null;
  /** 이번 실행이 만든 추천 id 목록 */
  recommendationIds: string[];
  /** 사장님에게 알릴 만한 일이었는지 — false면 조용히 넘어간다 */
  notified: boolean;
  /** 알리지 않았다면 그 이유 (예: "변화가 기준치 미만") */
  skipReason: string | null;
  /** 실패 시 사장님이 읽어도 되는 설명 */
  error: string | null;
  /** 실제 데이터 기반인지 예시인지 */
  origin: DataOrigin;
}

/** 알림을 보낸 채널 — 사장님은 앱보다 카카오톡에 있다 */
export type NotificationChannel = "kakao" | "push" | "email" | "sms";

/** 에이전트가 사장님에게 보낸 알림 한 건 */
export interface AgentNotification {
  /** 알림 고유 식별자 */
  id: string;
  /** 관련 실행 id */
  runId: string;
  /** 발송 채널 */
  channel: NotificationChannel;
  /** 알림 제목 */
  title: string;
  /** 알림 본문 (짧게, 존댓말) */
  body: string;
  /** 발송 시각 */
  sentAt: ISODateTime;
  /** 사장님이 읽은 시각 — 아직이면 null */
  readAt: ISODateTime | null;
  /** 눌렀을 때 이동할 앱 내 경로 */
  deepLink: string;
}

/**
 * 자율성 등급.
 * 돈이 나가거나 외부에 노출되는 행동은 반드시 승인을 거친다 (L3는 당분간 쓰지 않는다).
 */
export type AutonomyLevel =
  /** L0 — 화면에 보여주기만 */
  | "display_only"
  /** L1 — 변화가 있으면 알림 */
  | "notify"
  /** L2 — 추천까지 만들고, 실행은 사장님 승인 후 */
  | "recommend_with_approval"
  /** L3 — 승인 없이 실행 (현재 미사용) */
  | "autonomous";

/** 사장님이 조정할 수 있는 에이전트 설정 */
export interface AgentPolicy {
  /** 대상 매장 id */
  storeId: string;
  /** 자율성 등급 */
  autonomyLevel: AutonomyLevel;
  /** 정기 실행 시각 (cron 표현식, 예: "0 8 * * 1" = 매주 월요일 8시) */
  schedule: string;
  /** 알림 받을 채널 */
  channels: NotificationChannel[];
  /** 이 시간대에는 알리지 않는다 (예: 새벽 영업 중) */
  quietHours: { start: string; end: string } | null;
  /** 매출 증감이 이 값(%) 이상일 때만 알린다 */
  changeRateThreshold: number;
  /** 같은 패턴이 몇 주 반복되면 알릴지 */
  repeatWeeksThreshold: number;
}

/**
 * 에이전트 성적표.
 * "AI가 예측했습니다"로 끝내지 않고, 그 예측이 얼마나 맞았는지를 누적해 보여준다.
 */
export interface AgentHealth {
  /** 대상 매장 id */
  storeId: string;
  /** 집계 기준 시작일 */
  since: ISODate;
  /** 실행 횟수 */
  runCount: number;
  /** 검증된 예측 건수 */
  verifiedForecastCount: number;
  /** 예측 오차 평균 (%포인트, 절댓값) */
  avgAbsErrorPoints: number;
  /** 만든 추천 수 */
  recommendationCount: number;
  /** 사장님이 채택한 비율 (0~1) — 낮으면 추천이 쓸모없다는 뜻이다 */
  acceptedRate: number;
  /** 가장 많이 나온 거절 사유 — 없으면 null */
  topDeclineReason: string | null;
  /** 실제 데이터 기반인지 예시인지 */
  origin: DataOrigin;
}
