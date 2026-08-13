/**
 * 백엔드(FastAPI)와 주고받는 데이터 계약.
 * 프론트엔드는 이 파일의 타입만 신뢰하며, 목 데이터도 이 타입을 따른다.
 *
 * - 분석·예측 계약: 이 파일
 * - 행동 추천 계약: ./recommendation
 * - 에이전트 실행 계약: ./agent
 */

export * from "./agent";
export * from "./recommendation";

/* ------------------------------------------------------------------ */
/* 공통                                                                */
/* ------------------------------------------------------------------ */

/** ISO 8601 날짜 문자열 (YYYY-MM-DD) */
export type ISODate = string;

/** ISO 8601 일시 문자열 (YYYY-MM-DDTHH:mm:ss) */
export type ISODateTime = string;

/** 시작일~종료일로 표현되는 기간 (양 끝 포함) */
export interface DateRange {
  /** 기간 시작일 */
  start: ISODate;
  /** 기간 종료일 */
  end: ISODate;
}

/** 원화 금액 (단위: 원, 정수) */
export type Won = number;

/** 요일 (0=일요일 … 6=토요일) */
export type Weekday = 0 | 1 | 2 | 3 | 4 | 5 | 6;

/** 데이터가 실측인지 예시인지 구분하는 표식 — "예시 데이터" 배지 노출에 사용 */
export type DataOrigin = "real" | "sample";

/* ------------------------------------------------------------------ */
/* 매장                                                                */
/* ------------------------------------------------------------------ */

/** 매장 업종 */
export type StoreCategory = "cafe" | "restaurant" | "pub";

/** 사장님이 운영하는 매장 한 곳 */
export interface Store {
  /** 매장 고유 식별자 */
  id: string;
  /** 매장 상호명 */
  name: string;
  /** 업종 (카페/식당/주점) */
  category: StoreCategory;
  /** 개업일 — 영업 기간이 짧으면 데이터 충분성 판단에 사용 */
  openedAt: ISODate;
}

/* ------------------------------------------------------------------ */
/* 업로드 결과                                                          */
/* ------------------------------------------------------------------ */

/** 업로드 경고 심각도 — warning은 진행 가능, error는 재업로드 필요 */
export type UploadWarningLevel = "warning" | "error";

/** 업로드 경고 종류 (결측·이상치·형식 오류 등) */
export type UploadWarningCode =
  | "MISSING_VALUE"
  | "OUTLIER"
  | "DUPLICATE_ROW"
  | "UNPARSABLE_DATE"
  | "UNKNOWN_MENU"
  | "PERIOD_GAP";

/** CSV 파싱 중 발견된 문제 한 건 */
export interface UploadWarning {
  /** 경고 종류 코드 */
  code: UploadWarningCode;
  /** 심각도 */
  level: UploadWarningLevel;
  /** 사장님에게 그대로 보여줄 한국어 설명 문장 */
  message: string;
  /** 문제가 발생한 CSV 행 번호 목록 (헤더 제외, 1부터) */
  rowNumbers?: number[];
  /** 해당 경고에 걸린 행 수 */
  affectedRows: number;
}

/** POS 원본 메뉴명을 표준 메뉴명으로 정규화한 매핑 한 건 */
export interface MenuNormalization {
  /** POS에 기록된 원본 메뉴명 (예: "아아") */
  rawName: string;
  /** 정규화된 표준 메뉴명 (예: "아이스 아메리카노") */
  normalizedName: string;
  /** 매핑 신뢰도 0~1 — 낮으면 사장님 확인이 필요할 수 있음 */
  confidence: number;
  /** 이 원본명으로 집계된 판매 건수 */
  occurrences: number;
}

/** CSV 업로드 1회에 대한 처리 결과 요약 */
export interface UploadResult {
  /** 업로드 고유 식별자 */
  id: string;
  /** 대상 매장 id */
  storeId: string;
  /** 업로드된 파일명 */
  fileName: string;
  /** 업로드 처리 완료 시각 */
  uploadedAt: ISODateTime;
  /** 정상 처리된 행 수 */
  processedRows: number;
  /** 오류로 건너뛴 행 수 */
  skippedRows: number;
  /** 데이터가 커버하는 매출 기간 */
  period: DateRange;
  /** 인식된 표준 메뉴 개수 */
  recognizedMenuCount: number;
  /** 원본명 → 표준명 정규화 매핑 목록 */
  menuNormalizations: MenuNormalization[];
  /** 결측·이상치 등 경고 목록 (없으면 빈 배열) */
  warnings: UploadWarning[];
}

/* ------------------------------------------------------------------ */
/* 주간 분석                                                            */
/* ------------------------------------------------------------------ */

/** 주간 메뉴별 판매 실적 한 건 */
export interface MenuSales {
  /** 표준 메뉴명 */
  menuName: string;
  /** 판매 수량 */
  quantity: number;
  /** 해당 메뉴 매출액 */
  revenue: Won;
  /** 총매출 대비 비중 (%) */
  share: number;
}

/** 요일별 매출 한 건 */
export interface WeekdaySales {
  /** 요일 (0=일 … 6=토) */
  weekday: Weekday;
  /** 해당 요일 매출액 */
  revenue: Won;
  /** 해당 요일 주문 건수 */
  orderCount: number;
}

/** 시간대별 매출 한 건 (1시간 단위) */
export interface HourlySales {
  /** 시작 시각 (0~23) */
  hour: number;
  /** 해당 시간대 매출액 */
  revenue: Won;
  /** 해당 시간대 주문 건수 */
  orderCount: number;
}

/** 한 주(월~일)의 매출 분석 결과 */
export interface WeeklyAnalysis {
  /** 대상 매장 id */
  storeId: string;
  /** 분석 대상 주간 기간 */
  period: DateRange;
  /** 이 주의 총매출 */
  totalRevenue: Won;
  /** 전주 대비 증감률 (%, 음수는 감소) */
  changeRateVsPrevWeek: number;
  /** 비교 기준이 된 전주 총매출 — 없으면 null (첫 주) */
  prevWeekRevenue: Won | null;
  /** 판매량 상위 메뉴 목록 (내림차순) */
  topMenus: MenuSales[];
  /** 요일별 매출 (7개) */
  weekdaySales: WeekdaySales[];
  /** 시간대별 매출 (영업 시간대만) */
  hourlySales: HourlySales[];
  /** 실측 데이터인지 예시 데이터인지 */
  origin: DataOrigin;
}

/* ------------------------------------------------------------------ */
/* 예측                                                                */
/* ------------------------------------------------------------------ */

/** 예측 신뢰 수준 */
export type ConfidenceLevel = "high" | "medium" | "low";

/** 데이터 충분성 등급 — insufficient면 예측 대신 안내 문구를 보여준다 */
export type DataSufficiencyLevel = "sufficient" | "limited" | "insufficient";

/** 예측을 신뢰할 만한지에 대한 판단과 사장님용 안내 문구 */
export interface DataSufficiency {
  /** 충분성 등급 */
  level: DataSufficiencyLevel;
  /** 사장님에게 그대로 보여줄 문장 (예: "매출 데이터가 3주치뿐이라 예측을 만들 수 없습니다.") */
  message: string;
  /** 현재 확보된 주 수 */
  weeksAvailable: number;
  /** 예측에 필요한 최소 주 수 */
  weeksRequired: number;
}

/** 예측 수치를 뒷받침하는 근거 한 줄 — 수치 옆에 항상 함께 표시된다 */
export interface ForecastEvidence {
  /** 근거 제목 (예: "과거 시험 종료 직후 패턴") */
  label: string;
  /** 예상 증감률 중 이 근거가 기여한 비율 (%, 음수 가능) */
  contribution: number;
  /** 근거의 출처 (예: "매장 데이터 12주", "부산대 학사일정") */
  source: string;
  /** 필요 시 덧붙이는 한 줄 부연 설명 */
  detail?: string;
}

/** 학사일정 이벤트 종류 */
export type AcademicEventType =
  | "semester_start"
  | "semester_end"
  | "midterm"
  | "final"
  | "vacation"
  | "festival"
  | "holiday"
  | "entrance_exam"
  | "graduation";

/** 예측 기간과 겹치는 학사일정 이벤트 */
export interface AcademicEvent {
  /** 이벤트 이름 (예: "1학기 기말고사") */
  name: string;
  /** 시작일 */
  startDate: ISODate;
  /** 종료일 (하루짜리면 startDate와 동일) */
  endDate: ISODate;
  /** 이벤트 종류 */
  type: AcademicEventType;
}

/** 다음 주 수요 예측 결과 */
export interface Forecast {
  /** 대상 매장 id */
  storeId: string;
  /** 예측 대상 주간 기간 */
  targetWeek: DateRange;
  /** 예측 대상 주차 라벨 (예: "2026년 8월 3주차") */
  targetWeekLabel: string;
  /** 직전 주 대비 예상 증감률 (%, 음수는 감소) — dataSufficiency.level이 insufficient면 null */
  expectedChangeRate: number | null;
  /** 예측 신뢰 수준 — 예측이 없으면 null */
  confidence: ConfidenceLevel | null;
  /** 증감률의 근거 목록. contribution의 합은 expectedChangeRate와 일치해야 한다 */
  evidence: ForecastEvidence[];
  /** 예측 기간과 관련된 학사일정 이벤트 */
  academicEvents: AcademicEvent[];
  /** 데이터 충분성 — insufficient면 수치 대신 message를 표시한다 */
  dataSufficiency: DataSufficiency;
  /** 실측 데이터인지 예시 데이터인지 */
  origin: DataOrigin;
}

/* ------------------------------------------------------------------ */
/* 놓친 기회                                                            */
/* ------------------------------------------------------------------ */

/**
 * 품절·재고 부족으로 팔지 못했다고 추정되는 판매 기회 한 건.
 * 실제로 발생한 손실이 아니라 추정치이므로, 화면에서도 "손실"이 아니라
 * "예상 판매 기회"로만 표현한다.
 */
export interface MissedOpportunity {
  /** 고유 식별자 */
  id: string;
  /** 대상 매장 id */
  storeId: string;
  /** 발생일 */
  date: ISODate;
  /** 표준 메뉴명 */
  menuName: string;
  /** 추정 품절 시각 (HH:mm) */
  estimatedSoldOutAt: string;
  /** 평소 마감 시각 (HH:mm) */
  usualClosingAt: string;
  /** 팔 수 있었을 것으로 추정되는 금액 (실제 손실액이 아님) */
  estimatedOpportunity: Won;
  /** 같은 패턴이 몇 주 연속 반복됐는지 (1이면 이번이 처음) */
  repeatedWeeks: number;
  /** 이 추정의 근거를 설명하는 한 문장 */
  reasoning: string;
  /** 추정 신뢰 수준 */
  confidence: ConfidenceLevel;
  /** 실측 데이터인지 예시 데이터인지 */
  origin: DataOrigin;
}

/* ------------------------------------------------------------------ */
/* 예측 검증                                                            */
/* ------------------------------------------------------------------ */

/** 지난주 예측이 실제와 얼마나 맞았는지 되짚어보는 기록 */
export interface ForecastVerification {
  /** 대상 매장 id */
  storeId: string;
  /** 검증 대상이 된 주간 기간 */
  period: DateRange;
  /** 그때 예측했던 증감률 (%) */
  predictedChangeRate: number;
  /** 실제로 기록된 증감률 (%) */
  actualChangeRate: number;
  /** 오차 (실제 - 예측, %포인트) */
  errorPoints: number;
  /** 예측 당시 신뢰 수준 */
  predictedConfidence: ConfidenceLevel;
  /** 오차가 왜 생겼는지 설명하는 문장 */
  errorAnalysis: string;
  /** 이 오차를 모델에 반영했는지 여부 */
  reflectedInModel: boolean;
  /** 모델에 어떻게 반영했는지 한 줄 설명 — 반영하지 않았으면 null */
  reflectionNote: string | null;
  /** 실측 데이터인지 예시 데이터인지 */
  origin: DataOrigin;
}

/* ------------------------------------------------------------------ */
/* 콘텐츠 생성                                                          */
/* ------------------------------------------------------------------ */

/** 릴스 대본의 장면 한 컷 */
export interface ReelsScene {
  /** 장면 순서 (1부터) */
  order: number;
  /** 이 장면의 길이 (초) */
  durationSec: number;
  /** 화면에 무엇을 찍을지 (예: "아이스 아메리카노를 붓는 손 클로즈업") */
  visual: string;
  /** 화면에 얹을 자막 문구 */
  caption: string;
  /** 촬영 팁 한 줄 (선택) */
  tip?: string;
}

/** 예측·분석 결과를 홍보 콘텐츠로 옮긴 생성 결과 */
export interface ContentGeneration {
  /** 고유 식별자 */
  id: string;
  /** 대상 매장 id */
  storeId: string;
  /** 이 콘텐츠를 왜 지금 만드는지 요약한 상황 설명 (예: "다음 주 개강, 신입생 유입 예상") */
  situationSummary: string;
  /** 릴스 대본 장면 목록 (순서대로) */
  scenes: ReelsScene[];
  /** 게시글 캡션 본문 */
  caption: string;
  /** 해시태그 목록 (# 포함) */
  hashtags: string[];
  /** 추천 게시 시각 */
  recommendedPostAt: ISODateTime;
  /** 왜 그 시각을 추천하는지 한 줄 근거 */
  recommendedPostReason: string;
  /** 생성 시각 */
  generatedAt: ISODateTime;
  /** 실측 데이터인지 예시 데이터인지 */
  origin: DataOrigin;
}

/* ------------------------------------------------------------------ */
/* 대시보드 집계                                                        */
/* ------------------------------------------------------------------ */

/** 대시보드 한 화면에 필요한 데이터 묶음 */
export interface DashboardData {
  /** 대상 매장 */
  store: Store;
  /** 최근 주간 분석 */
  weeklyAnalysis: WeeklyAnalysis;
  /** 다음 주 예측 */
  forecast: Forecast;
  /** 놓친 기회 목록 */
  missedOpportunities: MissedOpportunity[];
  /** 지난주 예측 검증 — 첫 주에는 null */
  verification: ForecastVerification | null;
}
