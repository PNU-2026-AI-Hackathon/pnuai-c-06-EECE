import { AlertCircle, Check, Clock, MinusCircle } from "lucide-react";

import type { AgentRun, AgentStep } from "@/types";

import { MockDataBadge } from "@/components/common/mock-data-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

/** 실행 시각을 "08:00" 형태로 */
function timeOf(iso: string): string {
  return iso.slice(11, 16);
}

/** 단계 상태별 아이콘·색·라벨 — 색만으로 구분하지 않는다 */
const STEP_STYLE: Record<
  AgentStep["status"],
  { icon: typeof Check; ring: string; label: string }
> = {
  succeeded: { icon: Check, ring: "border-up bg-up text-primary-foreground", label: "완료" },
  skipped: { icon: MinusCircle, ring: "border-border bg-muted text-muted-foreground", label: "건너뜀" },
  failed: { icon: AlertCircle, ring: "border-down bg-down text-primary-foreground", label: "실패" },
};

/** 에이전트 실행 한 건의 단계별 기록 — "STAFFI가 한 일" */
export function AgentRunTimeline({ run }: { run: AgentRun }) {
  return (
    <Card className="shadow-none">
      <CardHeader className="pb-3">
        <div className="flex flex-wrap items-center gap-2">
          <CardTitle className="text-xl">STAFFI가 한 일</CardTitle>
          {run.origin === "sample" && <MockDataBadge />}
        </div>
        <p className="text-base text-muted-foreground">
          {run.trigger.description} · {run.startedAt.slice(0, 10).replaceAll("-", ".")}{" "}
          {timeOf(run.startedAt)} 시작
        </p>
      </CardHeader>

      <CardContent>
        {run.headline && (
          <p className="mb-6 rounded-lg bg-brand-soft p-4 text-lg font-semibold leading-relaxed">
            {run.headline}
          </p>
        )}

        <ol className="space-y-0">
          {run.steps.map((step, i) => {
            const style = STEP_STYLE[step.status];
            const Icon = style.icon;
            const last = i === run.steps.length - 1;

            return (
              <li key={step.order} className="flex gap-4">
                <div className="flex flex-col items-center">
                  <span
                    className={cn(
                      "flex size-8 shrink-0 items-center justify-center rounded-full border-2",
                      style.ring
                    )}
                  >
                    <Icon aria-hidden className="size-4" strokeWidth={3} />
                  </span>
                  {!last && <span aria-hidden className="w-0.5 flex-1 bg-border" />}
                </div>

                <div className={cn("min-w-0 flex-1", last ? "pb-0" : "pb-6")}>
                  <div className="flex flex-wrap items-baseline gap-x-3">
                    <p className="text-lg font-semibold">{step.label}</p>
                    <span className="tnum text-sm text-muted-foreground">
                      {timeOf(step.startedAt)} · {style.label}
                    </span>
                  </div>
                  <p className="mt-1 text-base leading-relaxed">{step.summary}</p>
                  {step.reason && (
                    <p className="mt-1 text-base text-muted-foreground">사유: {step.reason}</p>
                  )}
                </div>
              </li>
            );
          })}
        </ol>

        <div className="mt-6 flex items-center gap-2 border-t pt-4 text-base text-muted-foreground">
          <Clock aria-hidden className="size-4" />
          {run.notified
            ? `${run.recommendationIds.length}건의 추천을 만들어 알려드렸습니다.`
            : `알릴 만한 변화가 없어 조용히 넘어갔습니다. ${run.skipReason ?? ""}`}
        </div>
      </CardContent>
    </Card>
  );
}
