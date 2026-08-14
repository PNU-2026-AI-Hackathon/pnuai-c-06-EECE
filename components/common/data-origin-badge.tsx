import { Calculator, FlaskConical } from "lucide-react";

import { cn } from "@/lib/utils";
import type { DataOrigin } from "@/types";

/** 배지 크기 — 카드 제목 옆이면 default, 화면 상단 안내면 lg */
type BadgeSize = "default" | "lg";

/** "예시 데이터" 배지 — 실제 매장 데이터가 아님을 항상 눈에 보이게 알린다 */
export function MockDataBadge({
  className,
  label = "예시 데이터",
  size = "default",
}: {
  className?: string;
  /** 배지 문구 */
  label?: string;
  /** 카드 제목 옆이면 default, 화면 상단 안내면 lg */
  size?: BadgeSize;
}) {
  return (
    <BadgeShell className={className} size={size} icon={FlaskConical} label={label}>
      — 이 화면의 숫자는 실제 매장 데이터가 아니라 기능 확인용 예시입니다.
    </BadgeShell>
  );
}

/**
 * 숫자의 출처를 그대로 보여주는 배지.
 *
 * `real`은 배지를 달지 않고, `computed`와 `sample`은 문구를 다르게 단다.
 * 예시 CSV라도 실제 계산 엔진이 돌아 나온 값이면 손으로 적은 값과 같은 배지를 달아선 안 된다.
 */
export function DataOriginBadge({
  origin,
  className,
  size = "default",
}: {
  origin: DataOrigin;
  className?: string;
  size?: BadgeSize;
}) {
  if (origin === "real") return null;

  if (origin === "computed") {
    return (
      <BadgeShell className={className} size={size} icon={Calculator} label="예시 데이터로 계산">
        — 실제 매장 데이터는 아니지만, 이 숫자는 예시 매출 파일을 실제 분석 과정에 그대로 넣어
        계산한 결과입니다.
      </BadgeShell>
    );
  }

  return <MockDataBadge className={className} size={size} />;
}

/** 배지 겉모양 — 문구와 아이콘만 갈아 끼운다 */
function BadgeShell({
  className,
  size,
  icon: Icon,
  label,
  children,
}: {
  className?: string;
  size: BadgeSize;
  icon: typeof FlaskConical;
  label: string;
  /** 스크린리더에만 읽히는 보충 설명 */
  children: React.ReactNode;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border border-dashed border-primary/50 bg-brand-soft font-semibold text-accent-foreground",
        size === "lg" ? "px-3.5 py-1.5 text-base" : "px-2.5 py-1 text-sm",
        className
      )}
    >
      <Icon aria-hidden className={size === "lg" ? "size-4" : "size-3.5"} />
      {label}
      <span className="sr-only">{children}</span>
    </span>
  );
}
