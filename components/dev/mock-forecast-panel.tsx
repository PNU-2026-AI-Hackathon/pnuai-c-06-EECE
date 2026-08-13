"use client";

import type { Forecast } from "@/types";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { confidenceLabel, formatChangeRate, formatPeriod } from "@/lib/format";
import type { Mock } from "@/mocks";

/** 개발 전용 — 예측 목 데이터 확인 패널. 데이터 부족 시 수치 대신 안내 문구를 보여준다 */
export function MockForecastPanel({ forecast }: { forecast: Mock<Forecast> }) {
  const insufficient = forecast.dataSufficiency.level === "insufficient";
  const evidenceSum = forecast.evidence.reduce((s, e) => s + e.contribution, 0);

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-2">
          <div className="flex flex-wrap items-center gap-2">
            <CardTitle className="text-lg">{forecast.targetWeekLabel}</CardTitle>
            {forecast.isMockData && <Badge variant="secondary">예시 데이터</Badge>}
            {forecast.confidence && <Badge variant="outline">{confidenceLabel(forecast.confidence)}</Badge>}
          </div>
          <p className="text-sm text-muted-foreground">
            {formatPeriod(forecast.targetWeek.start, forecast.targetWeek.end)} · 매장 {forecast.storeId}
          </p>
        </CardHeader>
        <CardContent>
          {insufficient || forecast.expectedChangeRate === null ? (
            <Alert>
              <AlertTitle>데이터 부족</AlertTitle>
              <AlertDescription>
                {forecast.dataSufficiency.message}
                <span className="mt-1 block text-xs text-muted-foreground">
                  현재 {forecast.dataSufficiency.weeksAvailable}주 / 필요 {forecast.dataSufficiency.weeksRequired}주
                </span>
              </AlertDescription>
            </Alert>
          ) : (
            <div className="flex flex-wrap items-end gap-8">
              <div>
                <p className="text-sm text-muted-foreground">예상 증감률</p>
                <p className="text-4xl font-bold">{formatChangeRate(forecast.expectedChangeRate)}</p>
              </div>
              <div className="text-sm text-muted-foreground">
                <p>근거 합계 {formatChangeRate(evidenceSum)}</p>
                <p className={evidenceSum === forecast.expectedChangeRate ? "text-foreground" : "text-destructive"}>
                  {evidenceSum === forecast.expectedChangeRate ? "예상 증감률과 일치" : "불일치 — 데이터 확인 필요"}
                </p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">근거 ({forecast.evidence.length}건)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {forecast.evidence.length === 0 && (
            <p className="text-sm text-muted-foreground">예측을 만들지 않았으므로 근거도 없습니다.</p>
          )}
          {forecast.evidence.map((e) => (
            <div key={e.label} className="rounded-md border p-3">
              <div className="flex items-start justify-between gap-4">
                <p className="font-medium">{e.label}</p>
                <span className={e.contribution >= 0 ? "font-semibold" : "font-semibold text-destructive"}>
                  {formatChangeRate(e.contribution)}
                </span>
              </div>
              {e.detail && <p className="mt-1 text-sm text-muted-foreground">{e.detail}</p>}
              <p className="mt-1 text-xs text-muted-foreground">출처: {e.source}</p>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">관련 학사일정</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {forecast.academicEvents.map((ev) => (
            <div key={ev.name} className="flex items-center justify-between text-sm">
              <span className="font-medium">{ev.name}</span>
              <span className="text-muted-foreground">
                {ev.startDate} ~ {ev.endDate} · {ev.type}
              </span>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
