import Link from "next/link";
import { CalendarClock } from "lucide-react";

import type { DataFreshness } from "@/types";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/**
 * 데이터가 오래됐을 때의 안내.
 * 낡은 기준으로 계산한 숫자를 보여주느니 예측을 멈추고 새 파일을 요청한다 (원칙 2).
 */
export function DataFreshnessNotice({
  freshness,
  className,
}: {
  freshness: DataFreshness;
  className?: string;
}) {
  if (freshness.level === "fresh") return null;
  const blocking = freshness.blocksForecast;

  return (
    <div
      role="status"
      className={cn(
        "rounded-xl border-2 border-dashed p-6",
        blocking ? "border-down/40 bg-down-soft" : "border-border bg-secondary/60",
        className
      )}
    >
      <div className="flex gap-4">
        <CalendarClock aria-hidden className="mt-1 size-6 shrink-0 text-foreground" />
        <div className="min-w-0 flex-1 space-y-3">
          <h3 className="text-xl font-bold">
            {blocking ? "예측을 잠시 멈췄습니다" : "데이터가 조금 지났습니다"}
          </h3>
          <p className="text-base leading-relaxed">{freshness.message}</p>
          <p className="tnum text-base text-muted-foreground">
            마지막 매출 {freshness.lastDataDate.replaceAll("-", ".")} · {freshness.daysSinceLastData}일
            경과
          </p>
          {blocking && (
            <Button asChild size="lg" className="mt-1">
              <Link href="/settings">새 매출 파일 올리기</Link>
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
