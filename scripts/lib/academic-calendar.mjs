/**
 * 날짜에 학사일정을 붙인다.
 *
 * 실제 POS CSV에는 "학사이벤트" 컬럼이 없다. 그건 매장이 아니라 우리가 가진 정보다.
 * 그래서 매출 파일에서 읽지 않고, 날짜만 보고 우리 캘린더에서 찾아 붙인다.
 */

import fs from "node:fs";

/** 아무 일정도 겹치지 않는 평범한 수업일 */
export const DEFAULT_LABEL = "일반 학기";

/** 시험이 끝난 다음 주에 붙는 라벨 */
const postExamLabel = (examName) => `${examName} 종료 직후`;

/** 날짜 문자열 연산 (타임존을 타지 않도록 UTC로만 다룬다) */
function shift(date, days) {
  const d = new Date(`${date}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

/** 월요일이 주의 시작 */
function mondayOf(date) {
  const d = new Date(`${date}T00:00:00Z`);
  return shift(date, -((d.getUTCDay() + 6) % 7));
}

/** start~end의 모든 날짜 */
function eachDay(start, end) {
  const days = [];
  for (let d = start; d <= end; d = shift(d, 1)) days.push(d);
  return days;
}

export function loadCalendar(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

/**
 * 시험 다음 주 월~금을 "종료 직후" 구간으로 만든다.
 * 시험 주 자체가 아니라 그 다음 주여야 한다 — 시험이 끝나고 학생들이 다시 나오는 주다.
 */
function derivePostExamEvents(events) {
  return events
    .filter((e) => e.type === "midterm" || e.type === "final")
    .map((e) => {
      const start = shift(mondayOf(e.end), 7);
      return {
        name: postExamLabel(e.name),
        type: e.type,
        start,
        end: shift(start, 4),
        derived: true,
      };
    });
}

/**
 * 날짜 → 학사일정 라벨 맵.
 * 명시된 일정이 파생 일정을 이긴다. 기말 다음 주가 이미 겨울방학이면 방학이다.
 */
export function buildDayLabels(calendar) {
  const labels = new Map();

  for (const semester of calendar.semesters) {
    for (const event of derivePostExamEvents(semester.events)) {
      for (const day of eachDay(event.start, event.end)) {
        labels.set(day, { label: event.name, type: event.type, semesterId: semester.id });
      }
    }
  }

  for (const semester of calendar.semesters) {
    for (const event of semester.events) {
      for (const day of eachDay(event.start, event.end)) {
        labels.set(day, { label: event.name, type: event.type, semesterId: semester.id });
      }
    }
  }

  return labels;
}

/**
 * 아직 오지 않은 주의 하루하루를 만든다.
 *
 * 예측 대상 주에는 매출 기록이 없다. 그래서 CSV에서 꺼낼 수 없고 날짜로 만들어야 한다.
 * 요일과 학사일정만 있으면 예측에는 충분하다 — 그 둘이 우리가 미리 아는 전부다.
 */
export function buildFutureDays(calendar, startDate, count = 7) {
  const labels = buildDayLabels(calendar);
  return Array.from({ length: count }, (_, i) => {
    const date = shift(startDate, i);
    const hit = labels.get(date);
    return {
      date,
      weekday: new Date(`${date}T00:00:00Z`).getUTCDay(),
      event: hit?.label ?? DEFAULT_LABEL,
      eventType: hit?.type ?? null,
    };
  });
}

/** 이 날짜가 속한 학기 */
export function semesterOf(calendar, date) {
  return calendar.semesters.find((s) => s.start <= date && date <= s.end) ?? null;
}

/**
 * 일별 매출 레코드에 학사일정을 붙인다.
 * 캘린더가 못 덮는 날짜는 추측하지 않고 "일반 학기"로 두되, 몇 건인지 함께 돌려준다.
 */
export function attachAcademicEvents(rows, calendar) {
  const labels = buildDayLabels(calendar);
  let uncovered = 0;

  const labeled = rows.map((row) => {
    const hit = labels.get(row.date);
    const inSemester = semesterOf(calendar, row.date);
    if (!hit && !inSemester) uncovered += 1;
    return {
      ...row,
      event: hit?.label ?? DEFAULT_LABEL,
      eventType: hit?.type ?? null,
      semesterId: inSemester?.id ?? null,
    };
  });

  return { rows: labeled, uncovered };
}

/**
 * 해당 기간과 겹치는 학사일정을 화면용 이벤트로 추린다.
 * 라벨이 연속된 날짜는 하나로 묶는다 (중간고사 5일 = 이벤트 1개).
 */
export function eventsInRange(calendar, start, end) {
  const labels = buildDayLabels(calendar);
  const events = [];

  for (const day of eachDay(start, end)) {
    const hit = labels.get(day);
    if (!hit) continue;
    const last = events[events.length - 1];
    if (last && last.name === hit.label) last.endDate = day;
    else events.push({ name: hit.label, startDate: day, endDate: day, type: hit.type });
  }

  return events;
}
