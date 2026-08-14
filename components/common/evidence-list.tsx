import { AlertTriangle } from "lucide-react";

import type { ForecastEvidence } from "@/types";

import { directionOf } from "@/components/common/change-indicator";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { cn } from "@/lib/utils";

/**
 * 근거 합계와 예상 증감률이 어긋났다고 볼 오차 한계 (%p).
 * 기여도는 소수점까지 내려올 수 있으므로 표시 자릿수 아래의 차이는 불일치로 보지 않는다.
 */
const SUM_TOLERANCE = 0.05;

/** 증감률을 "+5%" / "−3%" 로 (부호에 진짜 마이너스 기호를 쓴다) */
function signed(value: number): string {
  const dir = directionOf(value);
  const sign = dir === "up" ? "+" : dir === "down" ? "−" : "";
  const abs = Math.abs(value);
  return `${sign}${Number.isInteger(abs) ? abs : abs.toFixed(1)}%`;
}

/** 기여도 막대 하나. 시각 요소일 뿐이므로 스크린리더에서는 숨기고 숫자로 읽게 한다 */
function ContributionBar({ contribution, max }: { contribution: number; max: number }) {
  const dir = directionOf(contribution);
  const width = max === 0 ? 0 : Math.round((Math.abs(contribution) / max) * 100);

  return (
    <div aria-hidden className="h-2.5 w-full overflow-hidden rounded-full bg-muted">
      <div
        className={cn("h-full rounded-full", dir === "down" ? "bg-down" : "bg-up")}
        style={{ width: `${Math.max(width, 4)}%` }}
      />
    </div>
  );
}

/**
 * 예측 근거 목록. 설계 원칙 1에 따라 예측 수치 옆에는 항상 이 목록이 붙는다.
 * 막대는 보조 표현이고, 기여도는 숫자와 부호로도 반드시 읽힌다.
 *
 * `total`을 주면 **근거의 합이 그 값과 맞는지 검증한다.** 어긋나면 숫자를 조용히
 * 보여주는 대신 경고를 띄운다 — 근거 없는 숫자를 보여주지 않는다는 원칙은
 * 백엔드를 믿는 것으로는 지켜지지 않기 때문이다 (docs/BACKEND_REQUEST.md 원칙 1).
 * 검증은 언제나 `items` 전체로 하고, `visibleCount`는 표시 개수만 줄인다.
 */
export function EvidenceList({
  items,
  total,
  visibleCount,
  caption = "예상 증감률의 근거",
  className,
}: {
  /** 근거 항목 — 일부만 보여주더라도 항상 전체를 넘긴다 */
  items: ForecastEvidence[];
  /** 이 근거들이 더해져 나와야 하는 예상 증감률. 주면 검증한다 */
  total?: number;
  /** 화면에 보여줄 개수 (검증은 전체 기준). 생략하면 전부 보여준다 */
  visibleCount?: number;
  /** 목록 제목 */
  caption?: string;
  className?: string;
}) {
  const max = Math.max(...items.map((i) => Math.abs(i.contribution)), 1);
  const sum = items.reduce((s, i) => s + i.contribution, 0);

  const visible = visibleCount === undefined ? items : items.slice(0, visibleCount);
  const hiddenCount = items.length - visible.length;
  const mismatch = total !== undefined && Math.abs(sum - total) > SUM_TOLERANCE;

  return (
    <section className={cn("space-y-4", className)} aria-label={caption}>
      <h3 className="text-base font-semibold text-muted-foreground">{caption}</h3>

      {mismatch && total !== undefined && (
        <Alert variant="destructive" className="border-2">
          <AlertTriangle aria-hidden className="size-5" />
          <AlertTitle className="text-base font-bold">숫자가 서로 맞지 않습니다</AlertTitle>
          <AlertDescription className="text-base">
            <p>
              아래 근거를 모두 더하면 <strong className="tnum">{signed(sum)}</strong>인데, 예상 증감률은{" "}
              <strong className="tnum">{signed(total)}</strong>로 나와 있습니다. 맞지 않는 숫자를 그대로
              보여드릴 수 없어 먼저 알려드립니다. 확인해서 바로잡겠습니다.
            </p>
          </AlertDescription>
        </Alert>
      )}

      <ul className="space-y-4">
        {visible.map((item) => {
          const dir = directionOf(item.contribution);
          const sign = dir === "up" ? "+" : dir === "down" ? "−" : "";
          return (
            <li key={item.label} className="space-y-2">
              <div className="flex items-start justify-between gap-4">
                <p className="font-semibold leading-snug">{item.label}</p>
                <p
                  className={cn(
                    "tnum shrink-0 text-lg font-bold",
                    dir === "down" ? "text-down" : dir === "up" ? "text-up" : "text-muted-foreground"
                  )}
                >
                  <span aria-hidden>
                    {sign}
                    {Math.abs(item.contribution)}%
                  </span>
                  <span className="sr-only">
                    {Math.abs(item.contribution)}퍼센트 {dir === "down" ? "감소" : "증가"} 요인
                  </span>
                </p>
              </div>
              <ContributionBar contribution={item.contribution} max={max} />
              {item.detail && <p className="text-base text-muted-foreground">{item.detail}</p>}
              <p className="text-sm text-muted-foreground">
                <span className="font-medium">근거: </span>
                {item.source}
              </p>
            </li>
          );
        })}
      </ul>

      {hiddenCount > 0 && (
        <p className="text-base text-muted-foreground">이 밖에 {hiddenCount}건이 더 있습니다.</p>
      )}

      {total !== undefined && hiddenCount === 0 && (
        <div className="flex items-center justify-between border-t pt-3">
          <p className="font-semibold">근거 합계</p>
          <p className={cn("tnum text-lg font-bold", mismatch && "text-destructive")}>{signed(sum)}</p>
        </div>
      )}
    </section>
  );
}
