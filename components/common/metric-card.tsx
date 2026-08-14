import type { ReactNode } from "react";

import type { DataOrigin } from "@/types";

import { ChangeIndicator } from "@/components/common/change-indicator";
import { DataOriginBadge } from "@/components/common/mock-data-badge";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

/** 핵심 지표 카드 — 큰 숫자 + 라벨 + 증감. 한 카드에 지표 하나만 담는다 */
export function MetricCard({
  label,
  value,
  unit,
  change,
  comparedTo = "지난주",
  changeUnit = "%",
  note,
  evidence,
  origin = "real",
  emphasis = "default",
  className,
}: {
  /** 지표 이름 (예: "이번 주 총매출") */
  label: string;
  /** 큰 숫자. 이미 포맷된 문자열을 받는다 (예: "326만원") */
  value: string;
  /** 숫자 뒤에 붙는 단위 (값 문자열에 단위가 없을 때만) */
  unit?: string;
  /** 증감 값. 없으면 증감 표시를 그리지 않는다 */
  change?: number;
  /** 증감 비교 대상 */
  comparedTo?: string;
  /** 증감 단위 — 퍼센트포인트면 "%p" */
  changeUnit?: string;
  /** 숫자 아래 한 줄 보조 설명 */
  note?: string;
  /** 이 숫자의 근거. 설계 원칙상 예측 수치에는 반드시 함께 표시한다 */
  evidence?: ReactNode;
  /** 예시 데이터 여부 */
  /** 이 숫자의 출처 — real이면 배지 없음 */
  origin?: DataOrigin;
  /** 화면에서 가장 중요한 지표 하나만 lg로 */
  emphasis?: "default" | "lg";
  className?: string;
}) {
  return (
    <Card className={cn("shadow-none", className)}>
      <CardContent className="space-y-3 p-6">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-base font-semibold text-muted-foreground">{label}</p>
          <DataOriginBadge origin={origin} />
        </div>

        <p className={cn("tnum text-foreground", emphasis === "lg" ? "text-metric-lg" : "text-metric")}>
          {value}
          {unit && <span className="ml-1 text-2xl font-semibold text-muted-foreground">{unit}</span>}
        </p>

        {change !== undefined && (
          <div className="flex flex-wrap items-center gap-2">
            <ChangeIndicator value={change} comparedTo={comparedTo} unit={changeUnit} size="lg" />
            <span className="text-base text-muted-foreground">{comparedTo} 대비</span>
          </div>
        )}

        {note && <p className="text-base text-muted-foreground">{note}</p>}
        {evidence && <div className="border-t pt-3">{evidence}</div>}
      </CardContent>
    </Card>
  );
}
