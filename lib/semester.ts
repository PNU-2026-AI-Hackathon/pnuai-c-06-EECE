import type { AcademicEvent, AcademicEventType, ISODate } from "@/types";

/** 학기 띠에 그릴 구간 하나 */
export interface SemesterSegment {
  /** 구간 이름 — 짧게 (예: "중간고사") */
  label: string;
  /** 구간 시작일 */
  start: ISODate;
  /** 구간 종료일 */
  end: ISODate;
  /** 띠에서 차지할 비율 (전체 대비 %) */
  ratio: number;
  /** 매출에 어떤 방향으로 작용하는 기간인지 — 색을 고르는 기준 */
  tone: "busy" | "quiet" | "normal";
  /** 라벨을 띠 안에 넣을 만큼 넓은지 */
  wide: boolean;
}

/** 학기 띠 전체 */
export interface SemesterRibbon {
  /** 학기 이름 (예: "2025학년도 2학기") */
  label: string;
  /** 구간들 (시간순) */
  segments: SemesterSegment[];
  /** 오늘 위치 (0~100%) */
  todayRatio: number;
  /** 오늘이 학기 안에 있는지 */
  todayInRange: boolean;
  /** 다음(또는 진행 중) 일정 */
  next: { event: AcademicEvent; daysUntil: number; ongoing: boolean } | null;
  /** 지금이 몇 주차인지 */
  weekNumber: number;
}

/** 이벤트 종류별로 매출이 오르는 기간인지 내리는 기간인지 */
const TONE: Record<AcademicEventType, SemesterSegment["tone"]> = {
  semester_start: "busy",
  festival: "busy",
  graduation: "busy",
  midterm: "quiet",
  final: "quiet",
  vacation: "quiet",
  entrance_exam: "quiet",
  holiday: "quiet",
  semester_end: "normal",
};

const DAY = 86_400_000;

/** 날짜 문자열을 UTC 타임스탬프로 (타임존 계산을 피한다) */
function toTime(date: ISODate): number {
  return new Date(`${date}T00:00:00Z`).getTime();
}

/** 두 날짜 사이의 일수 */
export function daysBetween(from: ISODate, to: ISODate): number {
  return Math.round((toTime(to) - toTime(from)) / DAY);
}

/**
 * 학사일정을 하나의 띠로 만든다.
 * 이벤트 사이의 빈 구간은 "일반 학기"로 채우고, 폭은 실제 기간에 비례한다.
 * 시험이 좁고 방학이 넓게 보이는 것 자체가 정보다.
 */
export function buildSemesterRibbon(
  events: AcademicEvent[],
  today: ISODate,
  label: string
): SemesterRibbon {
  const sorted = [...events].sort((a, b) => a.startDate.localeCompare(b.startDate));
  const start = sorted[0]?.startDate ?? today;
  const end = sorted[sorted.length - 1]?.endDate ?? today;
  const totalDays = Math.max(daysBetween(start, end), 1);

  const segments: SemesterSegment[] = [];
  let cursor = start;

  const push = (segLabel: string, segStart: ISODate, segEnd: ISODate, tone: SemesterSegment["tone"]) => {
    const days = Math.max(daysBetween(segStart, segEnd), 1);
    const ratio = (days / totalDays) * 100;
    segments.push({ label: segLabel, start: segStart, end: segEnd, ratio, tone, wide: ratio >= 9 });
  };

  for (const event of sorted) {
    if (daysBetween(cursor, event.startDate) > 0) {
      push("일반 학기", cursor, event.startDate, "normal");
    }
    push(event.name, event.startDate, event.endDate, TONE[event.type]);
    if (event.endDate > cursor) cursor = event.endDate;
  }

  const passed = daysBetween(start, today);
  const todayRatio = Math.min(Math.max((passed / totalDays) * 100, 0), 100);

  // 진행 중인 일정이 있으면 그것을, 없으면 앞으로 가장 가까운 일정을 고른다
  const ongoing = sorted.find((e) => e.startDate <= today && today <= e.endDate);
  const upcoming = sorted.find((e) => e.startDate > today);
  const target = ongoing ?? upcoming ?? null;

  return {
    label,
    segments,
    todayRatio,
    todayInRange: passed >= 0 && passed <= totalDays,
    next: target
      ? {
          event: target,
          daysUntil: daysBetween(today, target.startDate),
          ongoing: Boolean(ongoing),
        }
      : null,
    weekNumber: Math.max(Math.floor(passed / 7) + 1, 1),
  };
}

/** "중간고사 D-1" / "중간고사 진행 중" */
export function formatDday(next: SemesterRibbon["next"]): string | null {
  if (!next) return null;
  if (next.ongoing) return `${next.event.name} 기간`;
  if (next.daysUntil === 0) return `${next.event.name} 오늘 시작`;
  return `${next.event.name} D-${next.daysUntil}`;
}
