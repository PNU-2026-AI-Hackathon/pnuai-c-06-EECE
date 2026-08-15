import type { AcademicEvent, Store } from "@/types";

import { eventsInRange, semesterOf } from "./academic-calendar.mjs";
import { analyzeSales as analyzeSalesJs } from "./analyze.mjs";
import type { AnalysisResult } from "./types";

export type { AnalysisResult, AnalyzedStore, UnanalyzableStore } from "./types";

/** data/academic-calendar.json 의 학기 하나 */
export interface CalendarSemester {
  id: string;
  label: string;
  start: string;
  end: string;
  /** 공식 학사일정으로 확인된 값인지 */
  confirmed: boolean;
  events: { name: string; type: AcademicEvent["type"]; start: string; end: string }[];
}

export interface AcademicCalendar {
  school: string;
  semesters: CalendarSemester[];
}

/**
 * 매출 CSV 텍스트 하나로 화면에 필요한 모든 것을 계산한다.
 *
 * 계산 본체는 analyze.mjs 에 있다. 오프라인 스크립트와 업로드 API가 같은 코드를 쓰기 위해
 * JS로 두었고, 여기서 타입만 입혀 준다.
 */
export function analyzeSales(input: {
  csvText: string;
  fileName: string;
  calendar: AcademicCalendar;
  store: Pick<Store, "id" | "name" | "category">;
  /** 기준 시점. null이면 파일의 마지막 날짜를 쓴다 */
  today?: string | null;
}): AnalysisResult {
  return analyzeSalesJs({ today: null, ...input }) as AnalysisResult;
}

/**
 * 이 날짜가 속한 학기의 일정 — 학기 띠를 그리는 데 쓴다.
 * 캘린더가 덮지 못하는 날짜면 null. 없는 학기를 지어내지 않는다.
 */
export function semesterContextFor(
  calendar: AcademicCalendar,
  date: string
): { events: AcademicEvent[]; today: string; label: string } | null {
  const semester = semesterOf(calendar, date) as CalendarSemester | null;
  if (!semester) return null;
  return {
    events: eventsInRange(calendar, semester.start, semester.end) as AcademicEvent[],
    today: date,
    label: semester.label,
  };
}
