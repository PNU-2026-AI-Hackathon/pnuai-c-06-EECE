import type { Forecast, WeeklyAnalysis } from "@/types";

import { DataOriginBadge } from "@/components/common/data-origin-badge";
import { EvidenceList } from "@/components/common/evidence-list";
import { Card, CardContent } from "@/components/ui/card";
import { formatWon, formatWonShort } from "@/lib/format";

/** 만원 단위 숫자만 (단위는 작게 따로 붙인다) */
function toManwon(value: number): string {
  return Math.round(value / 10000).toLocaleString("ko-KR");
}

/**
 * 이번 주 예상 매출과 근거.
 * 근거는 EvidenceList에 맡긴다 — 합계가 예상 증감률과 어긋나면 그쪽이 경고를 띄운다.
 */
export function ForecastSummary({
  forecast,
  analysis,
}: {
  forecast: Forecast;
  analysis: WeeklyAnalysis;
}) {
  const range = forecast.expectedRange;
  if (!range) return null;

  const low = Math.round((analysis.totalRevenue * (100 + range.low)) / 100);
  const high = Math.round((analysis.totalRevenue * (100 + range.high)) / 100);
  const cases = forecast.comparableCases;

  return (
    <div className="space-y-3">
      <Card className="border-0 shadow-none">
        <CardContent className="p-6">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-base text-muted-foreground">이번 주 예상 매출</p>
            <DataOriginBadge origin={forecast.origin} />
          </div>
          <p className="tnum tight mt-2 text-metric">
            {toManwon(low)}~{toManwon(high)}
            <span className="ml-1.5 text-xl font-semibold text-muted-foreground">만원</span>
          </p>
          <p className="mt-2 text-base text-muted-foreground">
            지난주는 {formatWon(analysis.totalRevenue)}이었어요
          </p>
        </CardContent>
      </Card>

      <Card className="border-0 shadow-none">
        <CardContent className="p-6">
          <EvidenceList
            items={forecast.evidence}
            total={forecast.expectedChangeRate ?? undefined}
            caption="이렇게 본 이유"
          />

          <div className="mt-4 flex items-center justify-between gap-4 border-t pt-4 text-muted-foreground">
            <span className="text-base">비교한 사례</span>
            <span className="text-base">
              {cases.eventName} {cases.caseCount}번 ({cases.dayCount}일)
            </span>
          </div>
        </CardContent>
      </Card>

      {cases.caution && <p className="px-1 text-base text-muted-foreground">{cases.caution}</p>}

      <p className="px-1 text-sm text-muted-foreground">
        과거 같은 기간 실적으로 계산한 참고값이에요. 이 범위는 10번 중 약{" "}
        {Math.round(range.coverage / 10)}번 맞는 수준으로 잡았어요. 지난주 실적{" "}
        {formatWonShort(analysis.totalRevenue)} 기준입니다.
      </p>
    </div>
  );
}
