import type { ReactNode } from "react";
import { Info } from "lucide-react";

import type { DataSufficiency } from "@/types";

import { cn } from "@/lib/utils";

/** 진행 막대 — 몇 주가 더 쌓여야 예측이 시작되는지 보여준다 */
function WeeksProgress({ available, required }: { available: number; required: number }) {
  const percent = Math.min(Math.round((available / Math.max(required, 1)) * 100), 100);
  return (
    <div className="space-y-2">
      <div aria-hidden className="h-3 w-full overflow-hidden rounded-full bg-background">
        <div className="h-full rounded-full bg-primary" style={{ width: `${Math.max(percent, 6)}%` }} />
      </div>
      <p className="tnum text-base text-muted-foreground">
        지금까지 {available}주 · 예측 시작까지 {Math.max(required - available, 0)}주 남음
      </p>
    </div>
  );
}

/**
 * 데이터 부족 안내.
 * 설계 원칙 2에 따라, 데이터가 모자라면 추측한 숫자를 보여주는 대신 이 안내로 대체한다.
 */
export function DataInsufficientNotice({
  sufficiency,
  title = "아직 예측을 만들 수 없습니다",
  action,
  className,
}: {
  /** 백엔드가 내려준 데이터 충분성 정보 */
  sufficiency: DataSufficiency;
  /** 제목 문구 */
  title?: string;
  /** 하단에 놓을 버튼 등 */
  action?: ReactNode;
  className?: string;
}) {
  const limited = sufficiency.level === "limited";

  return (
    <div
      role="status"
      className={cn(
        "rounded-xl border-2 border-dashed p-6",
        limited ? "border-border bg-secondary/60" : "border-primary/30 bg-brand-soft/60",
        className
      )}
    >
      <div className="flex gap-4">
        <Info aria-hidden className="mt-1 size-6 shrink-0 text-primary" />
        <div className="min-w-0 flex-1 space-y-4">
          <div className="space-y-2">
            <h3 className="text-xl font-bold">{limited ? "참고용으로만 봐주세요" : title}</h3>
            <p className="text-base leading-relaxed text-foreground/90">{sufficiency.message}</p>
          </div>
          <WeeksProgress available={sufficiency.weeksAvailable} required={sufficiency.weeksRequired} />
          {action}
        </div>
      </div>
    </div>
  );
}
