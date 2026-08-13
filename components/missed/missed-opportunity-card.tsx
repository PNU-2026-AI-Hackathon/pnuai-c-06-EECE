import { AlertTriangle, Clock } from "lucide-react";

import type { MissedOpportunity } from "@/types";

import { MockDataBadge } from "@/components/common/mock-data-badge";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { confidenceLabel, formatDateShort, formatWon } from "@/lib/format";

/**
 * 놓친 기회 한 건.
 * 추정 금액 옆에는 항상 "어떻게 추정했는지"를 문장으로 붙인다 (설계 원칙 1).
 */
export function MissedOpportunityCard({
  item,
  isMockData = false,
}: {
  item: MissedOpportunity;
  isMockData?: boolean;
}) {
  const repeated = item.repeatedWeeks >= 2;

  return (
    <Card className="shadow-none">
      <CardContent className="space-y-4 p-6">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-xl font-bold">
            {formatDateShort(item.date)} {item.menuName}
          </h3>
          {repeated && (
            <Badge className="gap-1.5 bg-down text-base text-primary-foreground hover:bg-down">
              <AlertTriangle aria-hidden className="size-4" />
              {item.repeatedWeeks}주 연속
            </Badge>
          )}
          <Badge variant="outline" className="text-base font-medium">
            {confidenceLabel(item.confidence)}
          </Badge>
          {isMockData && <MockDataBadge />}
        </div>

        <div className="flex flex-wrap gap-x-10 gap-y-4">
          <div>
            <p className="text-base text-muted-foreground">추정 손실</p>
            <p className="tnum text-metric text-down">{formatWon(item.estimatedLoss)}</p>
          </div>
          <div>
            <p className="text-base text-muted-foreground">품절 추정 시각</p>
            <p className="tnum flex items-center gap-2 text-metric">
              <Clock aria-hidden className="size-7 text-muted-foreground" />
              {item.estimatedSoldOutAt}
            </p>
            <p className="text-base text-muted-foreground">평소 마감 {item.usualClosingAt}</p>
          </div>
        </div>

        <p className="rounded-lg bg-secondary p-4 text-base leading-relaxed">
          <span className="font-semibold">왜 이렇게 봤나: </span>
          {item.reasoning}
        </p>
      </CardContent>
    </Card>
  );
}
