import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { confidenceLabel, formatDateShort, formatWon } from "@/lib/format";
import { mockEarlySalesEnds } from "@/mocks";

const CONFIRMATION_LABEL = {
  unconfirmed: "확인 전",
  confirmed_sold_out: "품절 확인",
  other_reason: "다른 이유",
} as const;

/** 개발 전용 — 판매 조기 종료 후보 목 데이터 확인 패널 */
export function MockMissedPanel() {
  const m = mockEarlySalesEnds[0];
  const totalLow = mockEarlySalesEnds.reduce((s, o) => s + o.opportunityRange.low, 0);
  const totalHigh = mockEarlySalesEnds.reduce((s, o) => s + o.opportunityRange.high, 0);

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-2">
          <div className="flex flex-wrap items-center gap-2">
            <CardTitle className="text-lg">
              {formatDateShort(m.date)} {m.menuName} 조기 종료
            </CardTitle>
            <Badge variant="secondary">{m.repeatedWeeks}주 연속</Badge>
            <Badge variant="outline">{CONFIRMATION_LABEL[m.ownerConfirmation]}</Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-8">
            <div>
              <p className="text-sm text-muted-foreground">마지막 판매</p>
              <p className="text-2xl font-bold">{m.lastSoldAt}</p>
              <p className="text-xs text-muted-foreground">
                평소 마감 {m.usualClosingAt} · {m.earlierByMinutes}분 일찍
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">잠재 판매 기회</p>
              <p className="text-2xl font-bold">
                {formatWon(m.opportunityRange.low)} ~ {formatWon(m.opportunityRange.high)}
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">목록 전체 범위 합</p>
              <p className="text-2xl font-bold">
                {formatWon(totalLow)} ~ {formatWon(totalHigh)}
              </p>
            </div>
          </div>
          <div className="rounded-md bg-muted p-3 text-sm">
            <p>{m.reasoning}</p>
            <p className="mt-2 text-muted-foreground">원인 후보: {m.possibleCauses.join(", ")}</p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">전체 목록 ({mockEarlySalesEnds.length}건)</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>발생일</TableHead>
                <TableHead>메뉴</TableHead>
                <TableHead>마지막 판매</TableHead>
                <TableHead className="text-right">잠재 기회</TableHead>
                <TableHead className="text-right">반복</TableHead>
                <TableHead>신뢰도</TableHead>
                <TableHead>확인</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {mockEarlySalesEnds.map((o) => (
                <TableRow key={o.id}>
                  <TableCell>{formatDateShort(o.date)}</TableCell>
                  <TableCell className="font-medium">{o.menuName}</TableCell>
                  <TableCell>{o.lastSoldAt}</TableCell>
                  <TableCell className="text-right">
                    {formatWon(o.opportunityRange.low)} ~ {formatWon(o.opportunityRange.high)}
                  </TableCell>
                  <TableCell className="text-right">{o.repeatedWeeks}주</TableCell>
                  <TableCell>{confidenceLabel(o.confidence)}</TableCell>
                  <TableCell>{CONFIRMATION_LABEL[o.ownerConfirmation]}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
