import type { AcademicEvent } from "@/types";

/**
 * 부산대학교 2026학년도 2학기 학사일정 (시연용 요약본).
 * 예측 근거로 인용되며, 실제 서비스에서는 백엔드가 학사일정 API로 대체한다.
 */
export const mockAcademicCalendar2026Fall: AcademicEvent[] = [
  { name: "2학기 개강", startDate: "2026-09-01", endDate: "2026-09-01", type: "semester_start" },
  { name: "추석 연휴", startDate: "2026-09-24", endDate: "2026-09-26", type: "holiday" },
  { name: "개천절", startDate: "2026-10-03", endDate: "2026-10-03", type: "holiday" },
  { name: "한글날", startDate: "2026-10-09", endDate: "2026-10-09", type: "holiday" },
  { name: "2학기 중간고사", startDate: "2026-10-19", endDate: "2026-10-24", type: "midterm" },
  { name: "대학축제 (효원대동제)", startDate: "2026-11-04", endDate: "2026-11-06", type: "festival" },
  { name: "수능 (학사 휴업)", startDate: "2026-11-19", endDate: "2026-11-19", type: "entrance_exam" },
  { name: "2학기 기말고사", startDate: "2026-12-15", endDate: "2026-12-21", type: "final" },
  { name: "겨울방학 시작", startDate: "2026-12-22", endDate: "2027-02-28", type: "vacation" },
];

/** 예측 대상 주(2026-10-19~10-25)와 겹치는 학사일정만 추린 것 */
export const mockEventsForTargetWeek: AcademicEvent[] = [
  mockAcademicCalendar2026Fall[4],
];

/**
 * 부산대학교 2025학년도 2학기 — 술집 실데이터 시연용.
 * 날짜는 data/pub-sales-pnu-2025.csv 의 학사이벤트 라벨 구간과 일치한다.
 */
export const mockPnuFall2025: AcademicEvent[] = [
  { name: "개강", startDate: "2025-09-01", endDate: "2025-09-19", type: "semester_start" },
  { name: "중간고사", startDate: "2025-10-20", endDate: "2025-10-24", type: "midterm" },
  { name: "대학축제", startDate: "2025-11-10", endDate: "2025-11-14", type: "festival" },
  { name: "기말고사", startDate: "2025-12-15", endDate: "2025-12-19", type: "final" },
  { name: "겨울방학", startDate: "2025-12-20", endDate: "2026-02-28", type: "vacation" },
];
