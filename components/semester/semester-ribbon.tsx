import type { SemesterRibbon as Ribbon, SemesterSegment } from "@/lib/semester";

import { formatDday } from "@/lib/semester";
import { cn } from "@/lib/utils";

/** 구간 성격별 색 — 바쁜 기간은 파랑, 조용한 기간은 빨강 계열, 평소는 회색 */
const TONE_STYLE: Record<SemesterSegment["tone"], { bar: string; text: string }> = {
  busy: { bar: "bg-brand-soft", text: "text-accent-foreground" },
  quiet: { bar: "bg-down-soft", text: "text-down" },
  normal: { bar: "bg-secondary", text: "text-muted-foreground" },
};

/** 날짜를 "10월 20일"로 */
function formatMonthDay(date: string): string {
  const [, m, d] = date.split("-");
  return `${Number(m)}월 ${Number(d)}일`;
}

/**
 * 학기 전체를 하나의 띠로 보여준다.
 * 구간 폭이 곧 기간이라, 시험이 짧고 방학이 길다는 사실이 눈으로 읽힌다.
 * 띠를 못 읽어도 정보가 전달되도록 D-day는 글자로 크게 따로 쓴다.
 */
export function SemesterRibbon({ ribbon, className }: { ribbon: Ribbon; className?: string }) {
  const dday = formatDday(ribbon.next);
  const summary = ribbon.segments
    .map((s) => `${s.label} ${formatMonthDay(s.start)}부터`)
    .join(", ");

  return (
    <section className={cn("space-y-3", className)} aria-label="학기 일정">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        {dday && (
          <p className={cn("text-2xl font-bold tight", ribbon.next?.ongoing ? "text-down" : "text-foreground")}>
            {dday}
          </p>
        )}
        {ribbon.next && (
          <p className="text-base text-muted-foreground">
            {formatMonthDay(ribbon.next.event.startDate)} 시작
          </p>
        )}
      </div>

      <div>
        <div
          role="img"
          aria-label={`${ribbon.label} 일정입니다. ${summary}. 오늘은 ${ribbon.weekNumber}주차입니다.`}
          className="flex h-3 overflow-hidden rounded-full"
        >
          {ribbon.segments.map((segment) => (
            <div
              key={`${segment.label}-${segment.start}`}
              className={TONE_STYLE[segment.tone].bar}
              style={{ flex: `${segment.ratio} 0 0%` }}
            />
          ))}
        </div>

        {ribbon.todayInRange && (
          <div className="relative h-0">
            <span
              aria-hidden
              className="absolute -top-5 h-5 w-0.5 -translate-x-1/2 bg-foreground"
              style={{ left: `${ribbon.todayRatio}%` }}
            />
          </div>
        )}

        <div className="mt-2 flex justify-between text-sm text-muted-foreground">
          <span>{ribbon.segments[0]?.label ?? ""}</span>
          <span className="font-semibold text-foreground">
            오늘 · {ribbon.label} {ribbon.weekNumber}주차
          </span>
          <span>{ribbon.segments[ribbon.segments.length - 1]?.label ?? ""}</span>
        </div>
      </div>
    </section>
  );
}
