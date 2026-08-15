import type {
  EarlySalesEnd,
  Forecast,
  ForecastVerification,
  Store,
  UploadResult,
  WeeklyAnalysis,
} from "@/types";

/** analyzeSales() 가 계산해 낸 메타 정보 — "이 숫자 어디서 나왔나"에 답하는 근거 */
export interface AnalysisMeta {
  /** 사장님이 올린 파일 이름 */
  fileName: string;
  /** 기준 시점 — 이 날짜까지의 데이터만 예측에 사용했다 */
  asOf: string;
  /** 매출과 판매 수량에서 역산한 메뉴 단가 */
  estimatedPrices: Record<string, number>;
  /** 단가 역산의 최대 상대 오차 (0이면 완전히 일치) */
  priceEstimationMaxError: number;
  /** 학습에 사용한 완전한 주의 수 */
  weeksAvailable: number;
  /** 파일 형태 — 일별 집계인지 결제 내역인지 */
  shape: "daily" | "transaction";
  /** 학사일정을 붙이지 못한 날짜 수 (캘린더에 없는 기간) */
  uncoveredDays: number;
}

/** 최근 일별 매출 — 추세 확인용 */
export interface DailyPoint {
  date: string;
  weekday: number;
  event: string;
  revenue: number;
}

/** 분석에 성공한 결과 */
export interface AnalyzedStore {
  ok: true;
  meta: AnalysisMeta;
  store: Store;
  weeklyAnalysis: WeeklyAnalysis;
  forecast: Forecast;
  verification: ForecastVerification;
  upload: UploadResult;
  earlySalesEnds: EarlySalesEnd[];
  dataLimitations: string[];
  dailySeries: DailyPoint[];
}

/**
 * 파일은 읽었지만 분석까지는 못 간 경우.
 * 무엇이 부족한지 말해 주되, 없는 숫자를 지어내지 않는다.
 */
export interface UnanalyzableStore {
  ok: false;
  /** 사장님께 그대로 보여줄 한국어 문장 */
  reason: string;
  /** 파일을 읽은 결과는 여전히 보여줄 수 있다 */
  upload: UploadResult;
}

export type AnalysisResult = AnalyzedStore | UnanalyzableStore;
