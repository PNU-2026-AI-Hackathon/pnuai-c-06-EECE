"use client";

import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatChangeRate, formatPeriod, formatWon, formatWonShort, weekdayLabel } from "@/lib/format";
import { mockAnalysisNormal, mockHourlySales, mockWeekdaySales } from "@/mocks";

/** 개발 전용 — 주간 분석 목 데이터 확인 패널 */
export function MockAnalysisPanel() {
  const a = mockAnalysisNormal;
  const weekdayData = mockWeekdaySales.map((w) => ({
    name: weekdayLabel(w.weekday),
    매출: w.revenue,
  }));
  const hourlyData = mockHourlySales.map((h) => ({ name: `${h.hour}시`, 매출: h.revenue }));

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center gap-2">
            <CardTitle className="text-lg">mockAnalysisNormal</CardTitle>
            {a.isMockData && <Badge variant="secondary">예시 데이터</Badge>}
          </div>
          <p className="text-sm text-muted-foreground">{formatPeriod(a.period.start, a.period.end)}</p>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-8">
          <div>
            <p className="text-sm text-muted-foreground">총매출</p>
            <p className="text-2xl font-bold">{formatWon(a.totalRevenue)}</p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">전주 대비</p>
            <p className="text-2xl font-bold">{formatChangeRate(a.changeRateVsPrevWeek)}</p>
            <p className="text-xs text-muted-foreground">
              전주 {a.prevWeekRevenue ? formatWonShort(a.prevWeekRevenue) : "데이터 없음"} · 한글날·강한 비 포함
            </p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">합계 검증</p>
            <p className="text-2xl font-bold">
              {formatWonShort(a.topMenus.reduce((s, m) => s + m.revenue, 0))}
            </p>
            <p className="text-xs text-muted-foreground">메뉴별 합 = 총매출이어야 함</p>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">요일별 매출 (일요일 휴무)</CardTitle>
          </CardHeader>
          <CardContent className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={weekdayData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="name" tickLine={false} />
                <YAxis tickFormatter={(v) => formatWonShort(Number(v))} width={70} />
                <Tooltip formatter={(v) => formatWon(Number(v))} />
                <Bar dataKey="매출" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">시간대별 매출</CardTitle>
          </CardHeader>
          <CardContent className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={hourlyData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="name" tickLine={false} interval={1} />
                <YAxis tickFormatter={(v) => formatWonShort(Number(v))} width={70} />
                <Tooltip formatter={(v) => formatWon(Number(v))} />
                <Line type="monotone" dataKey="매출" stroke="hsl(var(--primary))" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">메뉴별 판매 TOP {a.topMenus.length}</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>메뉴</TableHead>
                <TableHead className="text-right">수량</TableHead>
                <TableHead className="text-right">매출</TableHead>
                <TableHead className="text-right">비중</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {a.topMenus.map((m) => (
                <TableRow key={m.menuName}>
                  <TableCell className="font-medium">{m.menuName}</TableCell>
                  <TableCell className="text-right">{m.quantity}</TableCell>
                  <TableCell className="text-right">{formatWon(m.revenue)}</TableCell>
                  <TableCell className="text-right">{m.share.toFixed(1)}%</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
