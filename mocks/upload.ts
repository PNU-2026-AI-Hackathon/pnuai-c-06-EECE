import type { MenuNormalization, UploadResult, UploadWarning } from "@/types";
import type { Mock } from "./types";

/**
 * POS에서 뽑은 원본 메뉴명은 표기가 제각각이다.
 * 같은 아이스 아메리카노가 "아아", "ICE아메리카노", "아메(ice)" 등으로 흩어져 있다.
 */
export const mockMenuNormalizations: MenuNormalization[] = [
  { rawName: "아아", normalizedName: "아이스 아메리카노", confidence: 0.98, occurrences: 1842 },
  { rawName: "ICE아메리카노", normalizedName: "아이스 아메리카노", confidence: 0.99, occurrences: 913 },
  { rawName: "아메리카노(L)", normalizedName: "아이스 아메리카노", confidence: 0.87, occurrences: 486 },
  { rawName: "아메 ice", normalizedName: "아이스 아메리카노", confidence: 0.94, occurrences: 274 },
  { rawName: "아메", normalizedName: "따뜻한 아메리카노", confidence: 0.71, occurrences: 655 },
  { rawName: "HOT아메", normalizedName: "따뜻한 아메리카노", confidence: 0.97, occurrences: 402 },
  { rawName: "카페라떼", normalizedName: "카페라떼", confidence: 1.0, occurrences: 1130 },
  { rawName: "라떼", normalizedName: "카페라떼", confidence: 0.82, occurrences: 517 },
  { rawName: "카페 라뗴", normalizedName: "카페라떼", confidence: 0.93, occurrences: 88 },
  { rawName: "바닐라라떼", normalizedName: "바닐라라떼", confidence: 1.0, occurrences: 604 },
  { rawName: "바라떼", normalizedName: "바닐라라떼", confidence: 0.89, occurrences: 231 },
  { rawName: "딸라", normalizedName: "딸기라떼", confidence: 0.76, occurrences: 143 },
  { rawName: "복숭아아이스티", normalizedName: "아이스티", confidence: 0.95, occurrences: 388 },
  { rawName: "복아티", normalizedName: "아이스티", confidence: 0.68, occurrences: 96 },
  { rawName: "자몽에이드", normalizedName: "자몽에이드", confidence: 1.0, occurrences: 275 },
  { rawName: "소금빵", normalizedName: "소금빵", confidence: 1.0, occurrences: 812 },
  { rawName: "소금빵(신)", normalizedName: "소금빵", confidence: 0.85, occurrences: 137 },
  { rawName: "크로플", normalizedName: "크로플", confidence: 1.0, occurrences: 264 },
  { rawName: "크로플+아이스크림", normalizedName: "크로플", confidence: 0.72, occurrences: 91 },
  { rawName: "TEST", normalizedName: "미분류", confidence: 0.1, occurrences: 14 },
];

/** CSV 파싱 중 발견된 문제들 — 시연에서 "그냥 넘어가지 않는다"를 보여주는 부분 */
export const mockUploadWarnings: UploadWarning[] = [
  {
    code: "PERIOD_GAP",
    level: "warning",
    message: "일요일 32일치 데이터가 없습니다. 정기 휴무로 판단해 분석에서 제외했습니다.",
    affectedRows: 0,
  },
  {
    code: "PERIOD_GAP",
    level: "warning",
    message: "2026년 9월 25일~26일 데이터가 없습니다. 추석 임시휴업으로 보입니다.",
    affectedRows: 0,
  },
  {
    code: "MISSING_VALUE",
    level: "warning",
    message: "결제금액이 비어 있는 행 23건을 제외했습니다.",
    rowNumbers: [418, 419, 1204, 1205, 1206],
    affectedRows: 23,
  },
  {
    code: "OUTLIER",
    level: "warning",
    message: "2026년 7월 14일 단일 결제 1,240,000원은 단체주문으로 보여 평균 계산에서 제외했습니다.",
    rowNumbers: [9871],
    affectedRows: 1,
  },
  {
    code: "DUPLICATE_ROW",
    level: "warning",
    message: "완전히 동일한 결제 기록 8건이 중복 입력되어 1건씩만 남겼습니다.",
    affectedRows: 8,
  },
  {
    code: "UNKNOWN_MENU",
    level: "warning",
    message: '메뉴명 "TEST" 14건은 어떤 메뉴인지 알 수 없어 미분류로 두었습니다.',
    affectedRows: 14,
  },
  {
    code: "UNPARSABLE_DATE",
    level: "error",
    message: "날짜 형식을 읽을 수 없는 행 3건을 제외했습니다. (예: 2026/13/01)",
    rowNumbers: [5522, 5523, 7810],
    affectedRows: 3,
  },
];

/** CSV 업로드 1회 결과 — 2026년 3월~10월 POS 내역 */
export const mockUploadResult: Mock<UploadResult> = {
  id: "upload_20261019_0913",
  storeId: "store_pnu_001",
  fileName: "ondam_pos_202603_202610.csv",
  uploadedAt: "2026-10-19T09:13:44",
  processedRows: 24762,
  skippedRows: 40,
  period: { start: "2026-03-02", end: "2026-10-18" },
  recognizedMenuCount: 11,
  menuNormalizations: mockMenuNormalizations,
  warnings: mockUploadWarnings,
  isMockData: true,
};

/** 데이터 부족 시나리오 — 개업 3주차 매장이 올린 짧은 CSV */
export const mockUploadResultShort: Mock<UploadResult> = {
  id: "upload_20261019_1102",
  storeId: "store_pnu_002",
  fileName: "brewinglab_pos_3weeks.csv",
  uploadedAt: "2026-10-19T11:02:07",
  processedRows: 1284,
  skippedRows: 6,
  period: { start: "2026-09-28", end: "2026-10-18" },
  recognizedMenuCount: 8,
  menuNormalizations: mockMenuNormalizations.slice(0, 6),
  warnings: [
    {
      code: "PERIOD_GAP",
      level: "warning",
      message: "매출 데이터가 3주치뿐입니다. 요일별 패턴을 판단하기에는 아직 부족합니다.",
      affectedRows: 0,
    },
  ],
  isMockData: true,
};
