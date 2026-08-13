import { CalendarDays } from "lucide-react";

import type { AcademicEvent } from "@/types";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatDateShort } from "@/lib/format";

/** 학사일정 종류별 한글 라벨 */
const TYPE_LABEL: Record<AcademicEvent["type"], string> = {
  semester_start: "개강",
  semester_end: "종강",
  midterm: "중간고사",
  final: "기말고사",
  vacation: "방학",
  festival: "축제",
  holiday: "공휴일",
  entrance_exam: "수능",
  graduation: "졸업식",
};

/** 예측 기간과 겹치는 학사일정. 데이터가 부족해도 이 정보는 확실하므로 항상 보여준다 */
export function AcademicEventList({
  events,
  title = "이 기간의 학사일정",
}: {
  events: AcademicEvent[];
  title?: string;
}) {
  return (
    <Card className="shadow-none">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-xl">
          <CalendarDays aria-hidden className="size-5 text-primary" />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {events.length === 0 ? (
          <p className="text-base text-muted-foreground">이 기간에는 특별한 학사일정이 없습니다.</p>
        ) : (
          <ul className="divide-y">
            {events.map((e) => (
              <li key={`${e.name}-${e.startDate}`} className="flex flex-wrap items-center justify-between gap-2 py-3">
                <span className="text-lg font-semibold">{e.name}</span>
                <span className="tnum text-base text-muted-foreground">
                  {formatDateShort(e.startDate)}
                  {e.startDate !== e.endDate && ` ~ ${formatDateShort(e.endDate)}`} · {TYPE_LABEL[e.type]}
                </span>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
