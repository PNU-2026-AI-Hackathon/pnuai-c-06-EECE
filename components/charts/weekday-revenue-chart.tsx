"use client";

import { Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, XAxis, YAxis } from "recharts";

import type { WeekdaySales } from "@/types";

import { formatWonShort, weekdayLabel } from "@/lib/format";

/**
 * 요일별 매출 막대 차트.
 * 텍스트 대안은 부모의 ChartFrame이 표로 제공하므로 여기서는 그림만 그린다.
 * 막대 위에 값을 직접 찍어 툴팁 없이도 숫자를 읽을 수 있게 한다.
 */
export function WeekdayRevenueChart({ data }: { data: WeekdaySales[] }) {
  const chartData = data.map((d) => ({
    name: weekdayLabel(d.weekday),
    revenue: d.revenue,
    closed: d.revenue === 0,
  }));
  const max = Math.max(...chartData.map((d) => d.revenue), 1);

  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} margin={{ top: 24, right: 8, left: 8, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />
          <XAxis
            dataKey="name"
            tickLine={false}
            axisLine={false}
            tick={{ fontSize: 16, fill: "hsl(var(--foreground))" }}
          />
          <YAxis
            tickFormatter={(v) => formatWonShort(Number(v))}
            tickLine={false}
            axisLine={false}
            width={64}
            domain={[0, Math.ceil(max / 100000) * 100000]}
            tick={{ fontSize: 14, fill: "hsl(var(--muted-foreground))" }}
          />
          <Bar dataKey="revenue" radius={[6, 6, 0, 0]} isAnimationActive={false}>
            {chartData.map((d) => (
              <Cell key={d.name} fill={d.closed ? "hsl(var(--muted))" : "hsl(var(--primary))"} />
            ))}
            <LabelList
              dataKey="revenue"
              position="top"
              formatter={(v: number) => (v === 0 ? "매출 없음" : formatWonShort(v))}
              style={{ fontSize: 14, fontWeight: 600, fill: "hsl(var(--foreground))" }}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
