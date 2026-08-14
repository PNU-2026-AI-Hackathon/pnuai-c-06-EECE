import { CheckCircle2, RefreshCcw } from "lucide-react";

import type { DataOrigin, ForecastVerification } from "@/types";

import { ChangeIndicator } from "@/components/common/change-indicator";
import { DataOriginBadge } from "@/components/common/mock-data-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatChangeRate, formatPeriod } from "@/lib/format";

/**
 * 지난주 예측이 얼마나 맞았는지.
 * 틀린 예측을 숨기지 않고 오차와 원인을 그대로 보여주는 것이 신뢰의 근거가 된다.
 */
export function VerificationCard({
  verification,
  origin = "real",
  compact = false,
}: {
  verification: ForecastVerification;
  /** 이 숫자의 출처 — real이면 배지 없음 */
  origin?: DataOrigin;
  /** 홈 화면처럼 좁은 자리에서는 오차 원인만 짧게 */
  compact?: boolean;
}) {
  const v = verification;
  const missed = Math.abs(v.errorPoints) >= 10;

  return (
    <Card className="shadow-none">
      <CardHeader className="pb-2">
        <div className="flex flex-wrap items-center gap-2">
          <CardTitle className="text-xl">지난주 예측은 맞았을까요?</CardTitle>
          <DataOriginBadge origin={origin} />
        </div>
        <p className="text-base text-muted-foreground">{formatPeriod(v.period.start, v.period.end)}</p>
      </CardHeader>

      <CardContent className="space-y-5">
        <div className="flex flex-wrap items-end gap-x-10 gap-y-4">
          <div>
            <p className="text-base text-muted-foreground">예측했던 값</p>
            <p className="tnum text-metric text-muted-foreground">{formatChangeRate(v.predictedChangeRate)}</p>
          </div>
          <div>
            <p className="text-base text-muted-foreground">실제</p>
            <p className="tnum text-metric">{formatChangeRate(v.actualChangeRate)}</p>
          </div>
          <div className="space-y-1">
            <p className="text-base text-muted-foreground">차이</p>
            <ChangeIndicator value={v.errorPoints} unit="%p" comparedTo="예측값" size="lg" />
          </div>
        </div>

        <p className="rounded-lg bg-secondary p-4 text-base leading-relaxed">
          <span className="font-semibold">{missed ? "빗나간 이유: " : "이렇게 봤습니다: "}</span>
          {v.errorAnalysis}
        </p>

        {!compact && (
          <div className="flex items-start gap-3 text-base">
            {v.reflectedInModel ? (
              <RefreshCcw aria-hidden className="mt-1 size-5 shrink-0 text-primary" />
            ) : (
              <CheckCircle2 aria-hidden className="mt-1 size-5 shrink-0 text-up" />
            )}
            <p>
              <span className="font-semibold">{v.reflectedInModel ? "다음 예측에 반영함: " : "모델 조정 없음: "}</span>
              {v.reflectedInModel ? v.reflectionNote : "오차가 크지 않아 예측 방식을 바꾸지 않았습니다."}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
