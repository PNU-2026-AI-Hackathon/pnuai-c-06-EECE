"use client";

import { Area, AreaChart, CartesianGrid, ReferenceArea, ResponsiveContainer, XAxis, YAxis } from "recharts";

import type { HourlySales } from "@/types";

import { formatWonShort } from "@/lib/format";

/**
 * 시간대별 매출 곡선.
 * 가장 매출이 높은 구간을 음영으로 표시해 "언제 바쁜가"를 한눈에 보이게 한다.
 */
export function HourlyRevenueChart({ data }: { data: HourlySales[] }) {
  const chartData = data.map((d) => ({ name: `${d.hour}시`, revenue: d.revenue, hour: d.hour }));
  const peak = chartData.reduce((a, b) => (b.revenue > a.revenue ? b : a), chartData[0]);

  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData} margin={{ top: 16, right: 8, left: 8, bottom: 0 }}>
          <defs>
            <linearGradient id="hourlyFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity={0.28} />
              <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity={0.03} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />
          <ReferenceArea
            x1={`${peak.hour - 1}시`}
            x2={`${peak.hour + 1}시`}
            fill="hsl(var(--primary))"
            fillOpacity={0.07}
          />
          <XAxis
            dataKey="name"
            tickLine={false}
            axisLine={false}
            interval={1}
            tick={{ fontSize: 14, fill: "hsl(var(--muted-foreground))" }}
          />
          <YAxis
            tickFormatter={(v) => formatWonShort(Number(v))}
            tickLine={false}
            axisLine={false}
            width={64}
            tick={{ fontSize: 14, fill: "hsl(var(--muted-foreground))" }}
          />
          <Area
            type="monotone"
            dataKey="revenue"
            stroke="hsl(var(--primary))"
            strokeWidth={3}
            fill="url(#hourlyFill)"
            isAnimationActive={false}
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
