import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

/** 로딩 자리표시자. 실제 레이아웃과 크기를 맞춰 화면이 튀지 않게 한다 */
export function LoadingSkeleton({
  variant = "card",
  count = 1,
  className,
}: {
  /** metric: 지표 카드, chart: 차트, table: 표, text: 문단, evidence: 근거 목록 */
  variant?: "metric" | "chart" | "table" | "text" | "evidence" | "card";
  /** 반복 개수 */
  count?: number;
  className?: string;
}) {
  const items = Array.from({ length: count });

  return (
    <div
      role="status"
      aria-live="polite"
      aria-busy="true"
      className={cn(variant === "metric" ? "grid gap-4 md:grid-cols-3" : "space-y-4", className)}
    >
      <span className="sr-only">불러오는 중입니다</span>

      {items.map((_, i) => {
        if (variant === "metric") {
          return (
            <Card key={i} className="shadow-none">
              <CardContent className="space-y-3 p-6">
                <Skeleton className="h-5 w-28" />
                <Skeleton className="h-10 w-40" />
                <Skeleton className="h-7 w-24" />
              </CardContent>
            </Card>
          );
        }

        if (variant === "chart") {
          return (
            <Card key={i} className="shadow-none">
              <CardContent className="space-y-4 p-6">
                <Skeleton className="h-6 w-40" />
                <Skeleton className="h-56 w-full" />
              </CardContent>
            </Card>
          );
        }

        if (variant === "table") {
          return (
            <Card key={i} className="shadow-none">
              <CardContent className="space-y-3 p-6">
                <Skeleton className="h-6 w-32" />
                {Array.from({ length: 5 }).map((__, r) => (
                  <div key={r} className="flex gap-4">
                    <Skeleton className="h-6 flex-1" />
                    <Skeleton className="h-6 w-20" />
                    <Skeleton className="h-6 w-24" />
                  </div>
                ))}
              </CardContent>
            </Card>
          );
        }

        if (variant === "evidence") {
          return (
            <div key={i} className="space-y-2">
              <div className="flex justify-between gap-4">
                <Skeleton className="h-6 w-56" />
                <Skeleton className="h-6 w-12" />
              </div>
              <Skeleton className="h-2.5 w-full rounded-full" />
              <Skeleton className="h-5 w-40" />
            </div>
          );
        }

        if (variant === "text") {
          return (
            <div key={i} className="space-y-2">
              <Skeleton className="h-5 w-full" />
              <Skeleton className="h-5 w-11/12" />
              <Skeleton className="h-5 w-2/3" />
            </div>
          );
        }

        return (
          <Card key={i} className="shadow-none">
            <CardContent className="space-y-3 p-6">
              <Skeleton className="h-6 w-40" />
              <Skeleton className="h-24 w-full" />
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
