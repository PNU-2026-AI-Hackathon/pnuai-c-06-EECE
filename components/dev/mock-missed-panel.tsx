"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { confidenceLabel, formatDateShort, formatWon } from "@/lib/format";
import { mockMissedOpportunities, mockMissedOpportunity } from "@/mocks";

/** 개발 전용 — 놓친 기회 목 데이터 확인 패널 */
export function MockMissedPanel() {
  const m = mockMissedOpportunity;
  const totalOpportunity = mockMissedOpportunities.reduce((s, o) => s + o.estimatedOpportunity, 0);

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-2">
          <div className="flex flex-wrap items-center gap-2">
            <CardTitle className="text-lg">
              {formatDateShort(m.date)} {m.menuName} 품절
            </CardTitle>
            <Badge variant="destructive">{m.repeatedWeeks}주 연속</Badge>
            {m.isMockData && <Badge variant="secondary">예시 데이터</Badge>}
            <Badge variant="outline">{confidenceLabel(m.confidence)}</Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-8">
            <div>
              <p className="text-sm text-muted-foreground">추정 품절 시각</p>
              <p className="text-2xl font-bold">{m.estimatedSoldOutAt}</p>
              <p className="text-xs text-muted-foreground">평소 마감 {m.usualClosingAt}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">예상 판매 기회</p>
              <p className="text-2xl font-bold">{formatWon(m.estimatedOpportunity)}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">전체 예상 기회 합</p>
              <p className="text-2xl font-bold">{formatWon(totalOpportunity)}</p>
            </div>
          </div>
          <p className="rounded-md bg-muted p-3 text-sm">{m.reasoning}</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">전체 목록 ({mockMissedOpportunities.length}건)</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>발생일</TableHead>
                <TableHead>메뉴</TableHead>
                <TableHead>품절 시각</TableHead>
                <TableHead className="text-right">예상 판매 기회</TableHead>
                <TableHead className="text-right">반복</TableHead>
                <TableHead>신뢰도</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {mockMissedOpportunities.map((o) => (
                <TableRow key={o.id}>
                  <TableCell>{formatDateShort(o.date)}</TableCell>
                  <TableCell className="font-medium">{o.menuName}</TableCell>
                  <TableCell>{o.estimatedSoldOutAt}</TableCell>
                  <TableCell className="text-right">{formatWon(o.estimatedOpportunity)}</TableCell>
                  <TableCell className="text-right">{o.repeatedWeeks}주</TableCell>
                  <TableCell>{confidenceLabel(o.confidence)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
