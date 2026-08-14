import { Info } from "lucide-react";

import type { Forecast } from "@/types";

import { DataOriginBadge } from "@/components/common/mock-data-badge";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { confidenceLabel, formatChangeRate, formatWonShort } from "@/lib/format";
import { cn } from "@/lib/utils";

/** 범위를 "−32% ~ −22%" 형태로 (낮은 쪽이 앞) */
function formatRange(low: number, high: number): string {
  return `${formatChangeRate(low)} ~ ${formatChangeRate(high)}`;
}

/**
 * 예측 결과 카드.
 * 단일 숫자만 크게 보여주면 실제보다 확실해 보이므로, 범위를 주인공으로 두고
 * 가장 가능성 높은 값과 비교 사례 수를 함께 보여준다.
 */
export function ForecastRangeCard({
  forecast,
  baseRevenue,
  className,
}: {
  forecast: Forecast;
  /** 비교 기준이 되는 이번 주 매출 — 예상 금액 범위를 계산한다 */
  baseRevenue: number;
  className?: string;
}) {
  const { expectedRange: range, expectedChangeRate: point, comparableCases: cases } = forecast;
  if (range === null || point === null) return null;

  const revenueLow = Math.round((baseRevenue * (100 + range.low)) / 100);
  const revenueHigh = Math.round((baseRevenue * (100 + range.high)) / 100);
  const down = range.high < 0;

  return (
    <Card className={cn("shadow-none", className)}>
      <CardContent className="space-y-5 p-6">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-base font-semibold text-muted-foreground">
            {forecast.targetWeekLabel} 예상 변화
          </p>
          {forecast.confidence && (
            <Badge variant="outline" className="text-base font-medium">
              {confidenceLabel(forecast.confidence)}
            </Badge>
          )}
          <DataOriginBadge origin={forecast.origin} />
        </div>

        <div className="space-y-2">
          <p className={cn("tnum text-metric-lg", down ? "text-down" : "text-up")}>
            {formatRange(range.low, range.high)}
          </p>
          <p className="text-lg text-muted-foreground">
            이번 주 대비 · 예상 매출 {formatWonShort(revenueLow)} ~ {formatWonShort(revenueHigh)}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-x-6 gap-y-2 border-t pt-4 text-base">
          <p>
            <span className="text-muted-foreground">가장 가능성 높은 값 </span>
            <span className="tnum font-bold">{formatChangeRate(point)}</span>
          </p>
          <p>
            <span className="text-muted-foreground">비교한 사례 </span>
            <span className="font-bold">
              {cases.eventName} {cases.caseCount}번 ({cases.dayCount}일)
            </span>
          </p>
        </div>

        {cases.caution && (
          <p className="flex gap-2 rounded-lg bg-secondary p-4 text-base leading-relaxed">
            <Info aria-hidden className="mt-0.5 size-5 shrink-0" />
            {cases.caution}
          </p>
        )}

        <p className="text-sm text-muted-foreground">
          과거 같은 기간의 실적을 기준으로 계산한 참고값이며, 실제 결과는 다를 수 있습니다. 이 범위는
          10번 중 약 {Math.round(range.coverage / 10)}번 맞는 수준으로 잡았습니다.
        </p>
      </CardContent>
    </Card>
  );
}
