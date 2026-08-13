import { LoadingSkeleton } from "@/components/common/loading-skeleton";

/** 주간 리포트 로딩 상태 */
export default function Loading() {
  return (
    <div className="space-y-8">
      <LoadingSkeleton variant="text" />
      <LoadingSkeleton variant="metric" count={3} />
      <LoadingSkeleton variant="chart" />
      <LoadingSkeleton variant="table" />
    </div>
  );
}
