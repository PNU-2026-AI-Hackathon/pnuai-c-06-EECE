"use client";

import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatDateShort, formatWon, formatWonShort } from "@/lib/format";
import { mockDailySales, mockUploadResult } from "@/mocks";

const WEATHER_LABEL: Record<string, string> = {
  clear: "맑음",
  cloudy: "흐림",
  rain: "비",
  heavy_rain: "강한 비",
};

/** 개발 전용 — 일별 원본 매출과 업로드 정규화 결과 확인 패널 */
export function MockRawPanel() {
  const chartData = mockDailySales.map((d) => ({
    name: formatDateShort(d.date),
    매출: d.revenue ?? 0,
  }));
  const closedDays = mockDailySales.filter((d) => d.revenue === null).length;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-2">
          <div className="flex flex-wrap items-center gap-2">
            <CardTitle className="text-base">일별 매출 {mockDailySales.length}일치 (결측 {closedDays}일)</CardTitle>
            <Badge variant="secondary">예시 데이터</Badge>
          </div>
          <p className="text-sm text-muted-foreground">휴무일은 0으로 그려집니다 — 값이 없는 날입니다</p>
        </CardHeader>
        <CardContent className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="name" tickLine={false} interval={4} fontSize={11} />
              <YAxis tickFormatter={(v) => formatWonShort(Number(v))} width={70} />
              <Tooltip formatter={(v) => formatWon(Number(v))} />
              <Area dataKey="매출" stroke="hsl(var(--primary))" fill="hsl(var(--primary))" fillOpacity={0.12} />
            </AreaChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">메뉴명 정규화 (원본 {mockUploadResult.menuNormalizations.length}종)</CardTitle>
          </CardHeader>
          <CardContent className="max-h-96 overflow-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>원본</TableHead>
                  <TableHead>표준</TableHead>
                  <TableHead className="text-right">신뢰도</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {mockUploadResult.menuNormalizations.map((n) => (
                  <TableRow key={n.rawName}>
                    <TableCell className="font-mono text-xs">{n.rawName}</TableCell>
                    <TableCell>{n.normalizedName}</TableCell>
                    <TableCell className={`text-right ${n.confidence < 0.8 ? "text-destructive" : ""}`}>
                      {(n.confidence * 100).toFixed(0)}%
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">업로드 경고 ({mockUploadResult.warnings.length}건)</CardTitle>
            <p className="text-sm text-muted-foreground">
              {mockUploadResult.processedRows.toLocaleString("ko-KR")}행 처리 · {mockUploadResult.skippedRows}행 제외
            </p>
          </CardHeader>
          <CardContent className="space-y-2">
            {mockUploadResult.warnings.map((w, i) => (
              <div key={i} className="rounded-md border p-3 text-sm">
                <div className="mb-1 flex items-center gap-2">
                  <Badge variant={w.level === "error" ? "destructive" : "outline"}>{w.code}</Badge>
                  <span className="text-xs text-muted-foreground">{w.affectedRows}행</span>
                </div>
                {w.message}
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">일별 원본 (노이즈 확인용)</CardTitle>
        </CardHeader>
        <CardContent className="max-h-96 overflow-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>날짜</TableHead>
                <TableHead className="text-right">매출</TableHead>
                <TableHead className="text-right">건수</TableHead>
                <TableHead>날씨</TableHead>
                <TableHead>비고</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {mockDailySales.map((d) => (
                <TableRow key={d.date} className={d.revenue === null ? "text-muted-foreground" : ""}>
                  <TableCell>{formatDateShort(d.date)}</TableCell>
                  <TableCell className="text-right">{d.revenue === null ? "—" : formatWon(d.revenue)}</TableCell>
                  <TableCell className="text-right">{d.orderCount ?? "—"}</TableCell>
                  <TableCell>{WEATHER_LABEL[d.weather]}</TableCell>
                  <TableCell className="text-sm">{d.note ?? ""}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
