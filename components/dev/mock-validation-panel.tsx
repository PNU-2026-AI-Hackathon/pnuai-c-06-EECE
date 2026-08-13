"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { confidenceLabel, formatChangeRate, formatPeriod } from "@/lib/format";
import { mockVerifications } from "@/mocks";

/** 개발 전용 — 예측 검증 목 데이터 확인 패널 (맞은 주 / 틀린 주 함께) */
export function MockValidationPanel() {
  return (
    <div className="space-y-4">
      {mockVerifications.map((v) => {
        const missed = Math.abs(v.errorPoints) >= 10;
        return (
          <Card key={v.period.start}>
            <CardHeader className="pb-2">
              <div className="flex flex-wrap items-center gap-2">
                <CardTitle className="text-lg">{formatPeriod(v.period.start, v.period.end)}</CardTitle>
                <Badge variant={missed ? "destructive" : "outline"}>{missed ? "크게 빗나감" : "근접"}</Badge>
                {v.isMockData && <Badge variant="secondary">예시 데이터</Badge>}
                <Badge variant="outline">예측 당시 {confidenceLabel(v.predictedConfidence)}</Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-wrap gap-8">
                <div>
                  <p className="text-sm text-muted-foreground">예측</p>
                  <p className="text-2xl font-bold">{formatChangeRate(v.predictedChangeRate)}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">실제</p>
                  <p className="text-2xl font-bold">{formatChangeRate(v.actualChangeRate)}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">오차</p>
                  <p className={`text-2xl font-bold ${missed ? "text-destructive" : ""}`}>
                    {formatChangeRate(v.errorPoints)}p
                  </p>
                </div>
              </div>
              <p className="rounded-md bg-muted p-3 text-sm">{v.errorAnalysis}</p>
              <p className="text-sm">
                <span className="font-medium">모델 반영: </span>
                {v.reflectedInModel ? v.reflectionNote : "반영하지 않음 (오차가 작아 조정 불필요)"}
              </p>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
