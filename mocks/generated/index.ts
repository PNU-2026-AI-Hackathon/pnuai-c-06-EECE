/**
 * CSV에서 생성된 실데이터 묶음.
 * store-data.json 은 scripts/build-store-data.mjs 가 만들며 직접 수정하지 않는다.
 * 여기서는 JSON을 계약 타입으로 좁혀 주기만 한다.
 */

import type {
  EarlySalesEnd,
  Forecast,
  ForecastVerification,
  Store,
  UploadResult,
  WeeklyAnalysis,
} from "@/types";

import raw from "./store-data.json";

/** 생성 메타 정보 — 시연 중 "이 숫자 어디서 나왔나" 질문에 답하는 근거 */
export interface GeneratedMeta {
  /** 원본 CSV 경로 */
  generatedFrom: string;
  /** 생성 시각 */
  generatedAt: string;
  /** 시연 기준 시점 — 이 날짜까지의 데이터만 예측에 사용했다 */
  demoToday: string;
  /** 매출과 판매 수량에서 역산한 메뉴 단가 */
  estimatedPrices: Record<string, number>;
  /** 단가 역산의 최대 상대 오차 (0이면 완전히 일치) */
  priceEstimationMaxError: number;
  /** 학습에 사용한 완전한 주의 수 */
  weeksAvailable: number;
}

/** 이 데이터로는 만들 수 없는 것들 — 화면에서 그대로 사장님께 알린다 */
export const dataLimitations: string[] = raw.dataLimitations;

export const generatedMeta = raw.meta as GeneratedMeta;
export const generatedStore = raw.store as Store;
export const generatedWeeklyAnalysis = raw.weeklyAnalysis as WeeklyAnalysis;
export const generatedForecast = raw.forecast as Forecast;
export const generatedVerification = raw.verification as ForecastVerification;
export const generatedUpload = raw.upload as UploadResult;

/**
 * 평소보다 일찍 끊긴 메뉴.
 * 결제 시각과 메뉴가 함께 있는 파일에서만 나온다 — 일별 집계 파일이면 빈 배열이다.
 */
export const generatedEarlySalesEnds = raw.earlySalesEnds as EarlySalesEnd[];

/** 최근 10주 일별 매출 — 추세 확인용 */
export const generatedDailySeries = raw.dailySeries as {
  date: string;
  weekday: number;
  event: string;
  revenue: number;
}[];
