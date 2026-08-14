"use client";

import { useState } from "react";
import { AlertTriangle, Check, Clock } from "lucide-react";

import type { EarlySalesEnd, OwnerConfirmation, SalesEndCause } from "@/types";

import { DataOriginBadge } from "@/components/common/mock-data-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { formatDateShort, formatWon } from "@/lib/format";

/** 원인 후보를 사장님이 읽을 말로 */
const CAUSE_LABEL: Record<SalesEndCause, string> = {
  sold_out: "재료가 떨어졌다",
  no_demand: "그 시간에 손님이 없었다",
  stopped_selling: "판매를 중단했다",
  early_closing: "일찍 마감했다",
  menu_renamed: "다른 이름으로 팔렸다",
  pos_missing: "POS 입력이 빠졌다",
};

/** 몇 분을 "5시간 40분"으로 */
function formatDuration(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m === 0 ? `${h}시간` : `${h}시간 ${m}분`;
}

/**
 * 판매 조기 종료 후보 한 건.
 * 시스템은 "품절"이라고 단정하지 않는다. 원인 후보를 보여주고 사장님이 확정한다.
 */
export function EarlySalesEndCard({ item }: { item: EarlySalesEnd }) {
  const [confirmation, setConfirmation] = useState<OwnerConfirmation>(item.ownerConfirmation);
  const [note, setNote] = useState(item.ownerNote);
  const repeated = item.repeatedWeeks >= 2;

  return (
    <Card className="shadow-none">
      <CardContent className="space-y-4 p-6">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-xl font-bold">
            {formatDateShort(item.date)} {item.menuName}
          </h3>
          {confirmation === "unconfirmed" && (
            <Badge variant="outline" className="gap-1.5 border-primary text-base font-semibold text-primary">
              확인 필요
            </Badge>
          )}
          {repeated && (
            <Badge className="gap-1.5 bg-secondary text-base text-secondary-foreground hover:bg-secondary">
              <AlertTriangle aria-hidden className="size-4" />
              {item.repeatedWeeks}주 연속
            </Badge>
          )}
          <DataOriginBadge origin={item.origin} />
        </div>

        <div className="flex flex-wrap gap-x-10 gap-y-4">
          <div>
            <p className="text-base text-muted-foreground">마지막 판매</p>
            <p className="tnum flex items-center gap-2 text-metric">
              <Clock aria-hidden className="size-7 text-muted-foreground" />
              {item.lastSoldAt}
            </p>
            <p className="text-base text-muted-foreground">
              평소 마감 {item.usualClosingAt} · {formatDuration(item.earlierByMinutes)} 일찍
            </p>
          </div>
          <div>
            <p className="text-base text-muted-foreground">잠재 판매 기회</p>
            <p className="tnum text-metric">
              {formatWon(item.opportunityRange.low)} ~ {formatWon(item.opportunityRange.high)}
            </p>
            <p className="text-base text-muted-foreground">
              실제 주문이 있었는지는 확인되지 않은 추정 범위입니다
            </p>
          </div>
        </div>

        <p className="rounded-lg bg-secondary p-4 text-base leading-relaxed">
          <span className="font-semibold">왜 이렇게 봤나: </span>
          {item.reasoning}
        </p>

        <div className="space-y-3 border-t pt-4">
          {confirmation === "unconfirmed" ? (
            <>
              <div>
                <p className="text-base font-semibold">그날 무슨 일이 있었나요?</p>
                <ul className="mt-2 list-disc space-y-1 pl-5 text-base text-muted-foreground">
                  {item.possibleCauses.map((cause) => (
                    <li key={cause}>{CAUSE_LABEL[cause]}</li>
                  ))}
                </ul>
              </div>
              <div className="flex flex-wrap gap-3">
                <Button size="lg" onClick={() => setConfirmation("confirmed_sold_out")}>
                  <Check aria-hidden className="mr-2 size-5" />
                  품절이었어요
                </Button>
                <Button
                  size="lg"
                  variant="outline"
                  onClick={() => {
                    setConfirmation("other_reason");
                    setNote(null);
                  }}
                >
                  다른 이유예요
                </Button>
              </div>
            </>
          ) : (
            <div className="flex flex-wrap items-center gap-3">
              <p className="text-base font-semibold">
                {confirmation === "confirmed_sold_out"
                  ? "품절로 확인하셨습니다. 다음부터 이 패턴을 미리 알려드릴게요."
                  : `다른 이유로 확인하셨습니다.${note ? ` — ${note}` : ""}`}
              </p>
              <Button size="lg" variant="ghost" onClick={() => setConfirmation("unconfirmed")}>
                되돌리기
              </Button>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
