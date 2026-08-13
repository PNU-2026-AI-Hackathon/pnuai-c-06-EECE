/**
 * 목 데이터 전용 보조 타입.
 * 백엔드 계약(types/index.ts)에는 존재하지 않으며, 화면 개발·시연용으로만 쓴다.
 */

/** 목 데이터임을 표시하는 플래그 — 화면에서 "예시 데이터" 배지를 자동으로 띄우는 데 사용 */
export interface MockFlag {
  /** 항상 true. 실제 API 응답에는 이 필드가 없다 */
  isMockData: true;
}

/** 계약 타입 T에 목 데이터 플래그를 덧붙인 형태 */
export type Mock<T> = T & MockFlag;

/** 그날의 날씨 — 매출 변동의 원인을 시연에서 설명하기 위한 부가 정보 */
export type MockWeather = "clear" | "cloudy" | "rain" | "heavy_rain";

/** 하루치 매출 원본 (POS 일별 집계). 휴무일은 revenue가 null이다 */
export interface MockDailySale {
  /** 영업일 */
  date: string;
  /** 요일 (0=일 … 6=토) */
  weekday: 0 | 1 | 2 | 3 | 4 | 5 | 6;
  /** 그날 매출 — 휴무로 데이터가 없으면 null */
  revenue: number | null;
  /** 주문 건수 — 휴무면 null */
  orderCount: number | null;
  /** 그날 날씨 */
  weather: MockWeather;
  /** 휴무·공휴일·이벤트 등 그날의 특이사항 — 없으면 null */
  note: string | null;
}
