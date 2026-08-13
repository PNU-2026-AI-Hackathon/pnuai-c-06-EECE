import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";

import { cn } from "@/lib/utils";

/** 증감 방향 — 색·화살표·부호 세 가지로 동시에 전달한다 (색맹 대응) */
export type ChangeDirection = "up" | "down" | "flat";

/** 증감률에서 방향을 계산 (0.05%p 미만은 변화 없음으로 본다) */
export function directionOf(value: number): ChangeDirection {
  if (value > 0.05) return "up";
  if (value < -0.05) return "down";
  return "flat";
}

const STYLE: Record<ChangeDirection, string> = {
  up: "bg-up-soft text-up",
  down: "bg-down-soft text-down",
  flat: "bg-muted text-muted-foreground",
};

const ICON = { up: ArrowUpRight, down: ArrowDownRight, flat: Minus };
const WORD: Record<ChangeDirection, string> = { up: "증가", down: "감소", flat: "변화 없음" };

/**
 * 증감 표시. 색만으로 정보를 전달하지 않도록 화살표와 +/- 부호를 항상 함께 보여준다.
 * 스크린리더에는 "지난주보다 5.6% 증가"처럼 문장으로 읽힌다.
 */
export function ChangeIndicator({
  value,
  comparedTo = "지난주",
  unit = "%",
  size = "default",
  className,
}: {
  /** 증감 값 (부호 포함) */
  value: number;
  /** 비교 대상 설명 */
  comparedTo?: string;
  /** 단위 — 퍼센트포인트면 "%p" */
  unit?: string;
  size?: "default" | "lg";
  className?: string;
}) {
  const dir = directionOf(value);
  const Icon = ICON[dir];
  const sign = dir === "up" ? "+" : dir === "down" ? "−" : "";
  const text = `${sign}${Math.abs(value).toFixed(1)}${unit}`;

  return (
    <span
      className={cn(
        "tnum inline-flex items-center gap-1.5 rounded-lg font-bold",
        STYLE[dir],
        size === "lg" ? "px-3 py-1.5 text-xl" : "px-2.5 py-1 text-base",
        className
      )}
    >
      <Icon aria-hidden className={size === "lg" ? "size-5" : "size-4"} strokeWidth={2.5} />
      <span aria-hidden>{text}</span>
      <span className="sr-only">
        {comparedTo}보다 {Math.abs(value).toFixed(1)}
        {unit === "%p" ? "퍼센트포인트" : "퍼센트"} {WORD[dir]}
      </span>
    </span>
  );
}
