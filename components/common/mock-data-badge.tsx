import { FlaskConical } from "lucide-react";

import { cn } from "@/lib/utils";

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
  size?: "default" | "lg";
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border border-dashed border-primary/50 bg-brand-soft font-semibold text-accent-foreground",
        size === "lg" ? "px-3.5 py-1.5 text-base" : "px-2.5 py-1 text-sm",
        className
      )}
    >
      <FlaskConical aria-hidden className={size === "lg" ? "size-4" : "size-3.5"} />
      {label}
      <span className="sr-only">
        — 이 화면의 숫자는 실제 매장 데이터가 아니라 기능 확인용 예시입니다.
      </span>
    </span>
  );
}
