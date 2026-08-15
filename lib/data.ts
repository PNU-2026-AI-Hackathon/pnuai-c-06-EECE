import type {
  AgentAction,
  AgentHealth,
  AgentRun,
  ContentGeneration,
  DataFreshness,
  Forecast,
  ForecastVerification,
  EarlySalesEnd,
  Recommendation,
  Store,
  UploadResult,
  WeeklyAnalysis,
} from "@/types";

import type { AcademicEvent } from "@/types";

import {
  mockAcademicCalendar2026Fall,
  mockAgentAction,
  mockAgentHealth,
  mockAgentRun,
  mockAnalysisNormal,
  mockContentGeneration,
  mockContentGenerationBasic,
  mockForecastConfident,
  mockForecastInsufficient,
  mockDataFreshness,
  mockDataFreshnessStale,
  mockEarlySalesEnds,
  mockPnuFall2025,
  mockRecommendations,
  mockStore,
  mockStoreNew,
  mockUploadResult,
  mockUploadResultShort,
  mockValidationMissed,
} from "@/mocks";
import {
  dataLimitations,
  generatedEarlySalesEnds,
  generatedForecast,
  generatedStore,
  generatedUpload,
  generatedVerification,
  generatedWeeklyAnalysis,
} from "@/mocks/generated";
import academicCalendar from "@/data/academic-calendar.json";
import { semesterContextFor, type AcademicCalendar } from "@/lib/analysis";
import { getUploadedAnalysis } from "@/lib/analysis/session-store";

/**
 * 데이터 접근 계층.
 *
 * 우선순위는 셋이다.
 *  1. 사장님이 방금 올린 파일의 분석 결과 (있으면 무조건 이것)
 *  2. 부산대 앞 술집 1년치 예시 CSV를 실제 파이프라인에 넣어 만든 기본 시연 데이터
 *  3. 시나리오(카페·데이터 부족 등)로 전환한 목 데이터
 *
 * 백엔드(FastAPI)가 생기면 이 파일의 구현만 fetch로 바꾼다.
 */

/** 지금 화면이 보여줄 데이터 — 업로드한 게 있으면 그 매장, 없으면 기본 시연 데이터 */
function current() {
  const uploaded = getUploadedAnalysis();
  if (uploaded) return { ...uploaded, fromUpload: true };
  return {
    store: generatedStore,
    weeklyAnalysis: generatedWeeklyAnalysis,
    forecast: generatedForecast,
    verification: generatedVerification,
    upload: generatedUpload,
    earlySalesEnds: generatedEarlySalesEnds,
    dataLimitations,
    fromUpload: false,
  };
}

/** 사장님이 올린 파일을 보고 있는지 — 화면에서 "예시 데이터" 안내를 감추는 데 쓴다 */
export async function isViewingUpload(): Promise<boolean> {
  return current().fromUpload;
}

/**
 * 화면 전환용 시나리오 — ?scenario=cafe 처럼 쿼리스트링으로 지정한다.
 * `mismatch`는 백엔드가 앞뒤가 안 맞는 예측을 보냈을 때 화면이 이를 잡아내는지 확인하는 용도다.
 */
export type Scenario = "default" | "cafe" | "insufficient" | "stale" | "mismatch";

/** 쿼리스트링 값을 시나리오로 변환 */
export function parseScenario(value?: string | string[]): Scenario {
  if (value === "cafe") return "cafe";
  if (value === "insufficient") return "insufficient";
  if (value === "stale") return "stale";
  if (value === "mismatch") return "mismatch";
  return "default";
}

/** 매장 정보 */
export async function getStore(scenario: Scenario = "default"): Promise<Store> {
  if (scenario === "insufficient") return mockStoreNew;
  if (scenario === "cafe") return mockStore;
  return current().store;
}

/** 최근 완료된 주의 매출 분석 */
export async function getWeeklyAnalysis(scenario: Scenario = "default"): Promise<WeeklyAnalysis> {
  if (scenario === "cafe") return mockAnalysisNormal;
  if (scenario === "insufficient") {
    return {
      ...mockAnalysisNormal,
      storeId: mockStoreNew.id,
      totalRevenue: 1284000,
      changeRateVsPrevWeek: 11.2,
      prevWeekRevenue: 1154000,
      topMenus: mockAnalysisNormal.topMenus.slice(0, 5),
    };
  }
  return current().weeklyAnalysis;
}

/** 다음 주 수요 예측 */
export async function getForecast(scenario: Scenario = "default"): Promise<Forecast> {
  if (scenario === "insufficient") return mockForecastInsufficient;
  if (scenario === "cafe") return mockForecastConfident;
  // 근거를 하나 빼서 합계를 일부러 어긋나게 만든다 — 화면이 이를 잡아내는지 확인하는 시나리오
  if (scenario === "mismatch") {
    const f = current().forecast;
    return { ...f, evidence: f.evidence.slice(0, 1) };
  }
  return current().forecast;
}

/** 판매 조기 종료 후보 (확인 안 된 것부터) */
export async function getEarlySalesEnds(scenario: Scenario = "default"): Promise<EarlySalesEnd[]> {
  if (scenario === "cafe") {
    return [...mockEarlySalesEnds].sort((a, b) =>
      a.ownerConfirmation === b.ownerConfirmation ? 0 : a.ownerConfirmation === "unconfirmed" ? -1 : 1
    );
  }
  // 결제 시각이 있는 파일이면 파이프라인이 채워 준다. 일별 집계면 빈 배열이고, 그때는 이유를 대신 보여준다.
  return [...current().earlySalesEnds].sort((a, b) =>
    a.ownerConfirmation === b.ownerConfirmation ? 0 : a.ownerConfirmation === "unconfirmed" ? -1 : 1
  );
}

/** 조기 종료를 탐지할 수 없는 이유 — 빈 목록 자리에 그대로 보여준다 */
export async function getEarlySalesEndLimitation(scenario: Scenario = "default"): Promise<string | null> {
  if (scenario === "cafe") return null;
  if (scenario === "insufficient") return "매출 데이터가 3주치뿐이라 반복되는 패턴을 판단할 수 없습니다.";
  if (current().earlySalesEnds.length > 0) return null;
  // 한계 문구는 파일 내용에 따라 달라지므로 순서가 아니라 내용으로 찾는다
  return current().dataLimitations.find((l) => l.includes("일찍 끝났는지")) ?? null;
}

/** 지난주 예측이 얼마나 맞았는지 — 첫 주에는 null */
export async function getLatestVerification(
  scenario: Scenario = "default"
): Promise<ForecastVerification | null> {
  if (scenario === "insufficient") return null;
  if (scenario === "cafe") return mockValidationMissed;
  return current().verification;
}

/** 가장 최근 CSV 업로드 결과 — 아직 올린 적 없으면 null */
export async function getLatestUpload(scenario: Scenario = "default"): Promise<UploadResult | null> {
  if (scenario === "insufficient") return mockUploadResultShort;
  if (scenario === "cafe") return mockUploadResult;
  return current().upload;
}

/** 이 데이터로 만들 수 없는 것들 */
export async function getDataLimitations(scenario: Scenario = "default"): Promise<string[]> {
  return scenario === "default" ? current().dataLimitations : [];
}

/**
 * 홍보 콘텐츠 생성 결과.
 * 아직 생성 엔진이 없어 사람이 만든 예시를 돌려준다 (origin: "sample").
 */
export async function getContent(scenario: Scenario = "default"): Promise<ContentGeneration> {
  // 예측을 못 하는 매장에는 예측을 인용하지 않는, 학사일정만 근거로 삼은 콘텐츠를 준다
  if (scenario === "insufficient") return mockContentGenerationBasic;
  return mockContentGeneration;
}

/* ------------------------------------------------------------------ */
/* 에이전트                                                            */
/* ------------------------------------------------------------------ */

/** 가장 최근 에이전트 실행 기록 */
export async function getLatestAgentRun(): Promise<AgentRun> {
  return mockAgentRun;
}

/** 아직 결정하지 않은 추천 (우선순위 높은 순) */
export async function getRecommendations(scenario: Scenario = "default"): Promise<Recommendation[]> {
  if (scenario === "insufficient") return [];
  const order = { high: 0, medium: 1, low: 2 };
  return [...mockRecommendations].sort((a, b) => order[a.priority] - order[b.priority]);
}

/** 추천에 딸린 실행 행동 — 없으면 undefined */
export async function getActionFor(recommendationId: string): Promise<AgentAction | undefined> {
  return mockAgentAction.recommendationId === recommendationId ? mockAgentAction : undefined;
}

/** 에이전트 성적표 */
export async function getAgentHealth(): Promise<AgentHealth> {
  return mockAgentHealth;
}

/** 데이터 신선도 — ?scenario=stale 로 예측 중단 화면을 확인할 수 있다 */
export async function getDataFreshness(scenario: Scenario = "default"): Promise<DataFreshness> {
  return scenario === "stale" ? mockDataFreshnessStale : mockDataFreshness;
}

/* ------------------------------------------------------------------ */
/* 학기                                                                */
/* ------------------------------------------------------------------ */

/** 학기 띠를 그리는 데 필요한 것 — 일정, 기준일, 학기 이름 */
export interface SemesterContext {
  /** 학기 전체 일정 */
  events: AcademicEvent[];
  /** 기준일 (시연에서는 고정) */
  today: string;
  /** 학기 이름 */
  label: string;
}

/**
 * 학기 일정.
 * 업로드한 파일이 있으면 그 파일의 기준 시점이 속한 학기를 찾아 그린다.
 * 기준일은 데이터의 마지막 날이다 — 실서비스에서는 오늘 날짜를 쓴다.
 */
export async function getSemesterContext(scenario: Scenario = "default"): Promise<SemesterContext> {
  if (scenario === "cafe") {
    return {
      events: mockAcademicCalendar2026Fall,
      today: "2026-10-18",
      label: "2026학년도 2학기",
    };
  }

  const uploaded = getUploadedAnalysis();
  if (uploaded) {
    const context = semesterContextFor(academicCalendar as AcademicCalendar, uploaded.meta.asOf);
    // 캘린더가 못 덮는 기간이면 학기 띠를 그릴 근거가 없다 — 기본 학기로 돌아간다
    if (context) return context;
  }

  return { events: mockPnuFall2025, today: "2025-10-19", label: "2025학년도 2학기" };
}
