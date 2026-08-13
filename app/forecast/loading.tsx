import { LoadingSkeleton } from "@/components/common/loading-skeleton";

/** 수요 예측 로딩 상태 */
export default function Loading() {
  return (
    <div className="space-y-8">
      <LoadingSkeleton variant="text" />
      <LoadingSkeleton variant="metric" count={2} />
      <LoadingSkeleton variant="evidence" count={4} />
    </div>
  );
}
