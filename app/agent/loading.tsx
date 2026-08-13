import { LoadingSkeleton } from "@/components/common/loading-skeleton";

/** STAFFI 활동 로딩 상태 */
export default function Loading() {
  return (
    <div className="space-y-8">
      <LoadingSkeleton variant="text" />
      <LoadingSkeleton variant="card" />
      <LoadingSkeleton variant="card" count={2} />
    </div>
  );
}
