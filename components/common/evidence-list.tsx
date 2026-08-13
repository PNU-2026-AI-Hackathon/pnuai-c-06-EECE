import type { ForecastEvidence } from "@/types";

import { directionOf } from "@/components/common/change-indicator";
import { cn } from "@/lib/utils";

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
 */
export function EvidenceList({
  items,
  total,
  caption = "예상 증감률의 근거",
  className,
}: {
  /** 근거 항목 */
  items: ForecastEvidence[];
  /** 합계로 보여줄 예상 증감률. 주면 하단에 합계 행을 그린다 */
  total?: number;
  /** 목록 제목 */
  caption?: string;
  className?: string;
}) {
  const max = Math.max(...items.map((i) => Math.abs(i.contribution)), 1);
  const sum = items.reduce((s, i) => s + i.contribution, 0);

  return (
    <section className={cn("space-y-4", className)} aria-label={caption}>
      <h3 className="text-base font-semibold text-muted-foreground">{caption}</h3>

      <ul className="space-y-4">
        {items.map((item) => {
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

      {total !== undefined && (
        <div className="flex items-center justify-between border-t pt-3">
          <p className="font-semibold">근거 합계</p>
          <p className="tnum text-lg font-bold">
            {sum > 0 ? "+" : sum < 0 ? "−" : ""}
            {Math.abs(sum)}%
          </p>
        </div>
      )}
    </section>
  );
}
