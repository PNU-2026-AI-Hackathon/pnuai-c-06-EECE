import type { AgentHealth, DataFreshness } from "@/types";

import { DataOriginBadge } from "@/components/common/data-origin-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

/** 신선도 등급별 표현 — 색과 문구를 함께 쓴다 */
const FRESHNESS: Record<DataFreshness["level"], { label: string; className: string }> = {
  fresh: { label: "최신", className: "bg-up-soft text-up" },
  aging: { label: "조금 지남", className: "bg-secondary text-secondary-foreground" },
  stale: { label: "오래됨", className: "bg-down-soft text-down" },
};

/**
 * 에이전트 성적표.
 * "AI가 예측했습니다"로 끝내지 않고, 그동안 얼마나 맞았는지를 숫자로 남긴다.
 */
export function AgentHealthCard({
  health,
  freshness,
}: {
  health: AgentHealth;
  freshness: DataFreshness;
}) {
  const f = FRESHNESS[freshness.level];

  return (
    <Card className="shadow-none">
      <CardHeader className="pb-2">
        <div className="flex flex-wrap items-center gap-2">
          <CardTitle className="text-xl">STAFFI 성적표</CardTitle>
          <DataOriginBadge origin={health.origin} />
        </div>
        <p className="text-base text-muted-foreground">
          {health.since.replaceAll("-", ".")}부터 {health.runCount}번 일했습니다
        </p>
      </CardHeader>

      <CardContent className="space-y-5">
        <div className="grid gap-5 sm:grid-cols-3">
          <div>
            <p className="text-base text-muted-foreground">범위 안에 들어온 비율</p>
            <p className="tnum text-metric">
              {Math.round(health.rangeHitRate * 100)}
              <span className="ml-1 text-xl font-semibold text-muted-foreground">%</span>
            </p>
            <p className="text-sm text-muted-foreground">
              검증 {health.verifiedForecastCount}건 중{" "}
              {Math.round(health.rangeHitRate * health.verifiedForecastCount)}건
            </p>
          </div>
          <div>
            <p className="text-base text-muted-foreground">오르내림 방향</p>
            <p className="tnum text-metric">
              {Math.round(health.directionAccuracy * 100)}
              <span className="ml-1 text-xl font-semibold text-muted-foreground">%</span>
            </p>
            <p className="text-sm text-muted-foreground">
              평균 오차 {health.avgAbsErrorPoints}%p · {Math.round(health.avgAbsErrorWon / 10000)}만원
            </p>
          </div>
          <div>
            <p className="text-base text-muted-foreground">추천 채택률</p>
            <p className="tnum text-metric">
              {Math.round(health.acceptedRate * 100)}
              <span className="ml-1 text-xl font-semibold text-muted-foreground">%</span>
            </p>
            <p className="text-sm text-muted-foreground">추천 {health.recommendationCount}건 중</p>
          </div>
          <div>
            <p className="text-base text-muted-foreground">데이터 상태</p>
            <p className="mt-1">
              <span className={cn("inline-block rounded-lg px-3 py-1.5 text-xl font-bold", f.className)}>
                {f.label}
              </span>
            </p>
            <p className="text-sm text-muted-foreground">
              {freshness.lastDataDate.replaceAll("-", ".")}까지 · {freshness.daysSinceLastData}일 경과
            </p>
          </div>
        </div>

        <p className="rounded-lg bg-secondary p-4 text-base leading-relaxed">{freshness.message}</p>

        {health.topDeclineReason && (
          <p className="text-base text-muted-foreground">
            사장님이 가장 많이 고른 거절 사유는 &quot;이미 하고 있어요&quot;였습니다. 이런 추천은 줄여
            나가겠습니다.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
