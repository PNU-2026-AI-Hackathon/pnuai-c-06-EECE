import Link from "next/link";
import { ArrowRight, Check, Minus, TriangleAlert } from "lucide-react";

import type { UploadResult } from "@/types";

import { DataOriginBadge } from "@/components/common/data-origin-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatPeriod } from "@/lib/format";
import { cn } from "@/lib/utils";

/** 업로드한 파일을 읽은 결과 — 무엇이 되고 무엇이 안 되는지 먼저 알린다 */
export function UploadSummary({
  result,
  /** 분석까지 성공했는지 — 실패했으면 "결과 보러 가기"를 띄우지 않는다 */
  analyzed = true,
}: {
  result: UploadResult;
  analyzed?: boolean;
}) {
  const usable = result.capabilities.filter((c) => c.available);
  const blocked = result.capabilities.filter((c) => !c.available);
  const lowConfidence = result.menuNormalizations.filter((m) => m.confidence < 0.8);

  return (
    <div className="space-y-5">
      <Card className="shadow-none">
        <CardHeader className="pb-2">
          <div className="flex flex-wrap items-center gap-2">
            <CardTitle className="text-xl">파일을 읽었습니다</CardTitle>
            <DataOriginBadge origin="computed" />
          </div>
          <p className="text-base text-muted-foreground">{result.fileName}</p>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="grid gap-5 sm:grid-cols-3">
            <div>
              <p className="text-base text-muted-foreground">읽은 기록</p>
              <p className="tnum text-metric">{result.processedRows.toLocaleString("ko-KR")}</p>
              <p className="text-sm text-muted-foreground">
                {result.skippedRows > 0 ? `${result.skippedRows}건 제외` : "제외된 기록 없음"}
              </p>
            </div>
            <div>
              <p className="text-base text-muted-foreground">기간</p>
              <p className="tnum text-2xl font-bold leading-tight">
                {formatPeriod(result.period.start, result.period.end)}
              </p>
              <p className="text-sm text-muted-foreground">완전한 주 {result.weeksCovered}주</p>
            </div>
            <div>
              <p className="text-base text-muted-foreground">인식한 메뉴</p>
              <p className="tnum text-metric">{result.recognizedMenuCount}</p>
              <p className="text-sm text-muted-foreground">
                {lowConfidence.length > 0 ? `${lowConfidence.length}개는 확인이 필요합니다` : "모두 명확합니다"}
              </p>
            </div>
          </div>

          <div className="space-y-3 border-t pt-4">
            <p className="text-base font-semibold">이 파일로 할 수 있는 것</p>
            <ul className="space-y-2">
              {[...usable, ...blocked].map((c) => (
                <li key={c.kind} className="flex gap-3">
                  {c.available ? (
                    <Check aria-hidden className="mt-1 size-5 shrink-0 text-up" strokeWidth={3} />
                  ) : (
                    <Minus aria-hidden className="mt-1 size-5 shrink-0 text-muted-foreground" strokeWidth={3} />
                  )}
                  <div className="min-w-0">
                    <p className={cn("text-base font-medium", !c.available && "text-muted-foreground")}>
                      {c.label}
                      {!c.available && " — 지금은 불가"}
                    </p>
                    {c.missingReason && (
                      <p className="text-base text-muted-foreground">{c.missingReason}</p>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          </div>

          {result.warnings.length > 0 && (
            <div className="space-y-2 border-t pt-4">
              <p className="text-base font-semibold">확인해 주실 것 {result.warnings.length}건</p>
              {result.warnings.map((w, i) => (
                <div key={i} className="flex gap-3 rounded-lg bg-secondary p-3">
                  <TriangleAlert
                    aria-hidden
                    className={cn("mt-0.5 size-5 shrink-0", w.level === "error" ? "text-down" : "text-muted-foreground")}
                  />
                  <p className="text-base">{w.message}</p>
                </div>
              ))}
            </div>
          )}

          {analyzed && (
            <div className="flex flex-wrap items-center gap-3 border-t pt-4">
              <Button asChild size="lg">
                <Link href="/">
                  분석 결과 보러 가기
                  <ArrowRight aria-hidden className="ml-2 size-4" />
                </Link>
              </Button>
              <p className="text-sm text-muted-foreground">
                홈·주간 리포트·수요 예측이 모두 이 파일로 다시 계산되었습니다.
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {lowConfidence.length > 0 && (
        <Card className="shadow-none">
          <CardHeader className="pb-2">
            <CardTitle className="text-xl">같은 메뉴인지 확인해 주세요</CardTitle>
            <p className="text-base text-muted-foreground">
              이름이 비슷하지만 다른 메뉴일 수 있어 자동으로 묶지 않았습니다.
            </p>
          </CardHeader>
          <CardContent className="space-y-3">
            {lowConfidence.slice(0, 6).map((m) => (
              <div key={m.rawName} className="flex flex-wrap items-center gap-3 rounded-lg border p-3">
                <span className="font-mono text-base">{m.rawName}</span>
                <span aria-hidden className="text-muted-foreground">
                  →
                </span>
                <span className="text-base font-semibold">{m.normalizedName}</span>
                <Badge variant="outline" className="text-sm">
                  {m.occurrences.toLocaleString("ko-KR")}건
                </Badge>
                <div className="ml-auto flex gap-2">
                  <Button size="sm" variant="secondary">
                    같은 메뉴로 묶기
                  </Button>
                  <Button size="sm" variant="ghost">
                    각각 두기
                  </Button>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
