import { LoadingSkeleton } from "@/components/common/loading-skeleton";

/** 홍보 콘텐츠 로딩 상태 */
export default function Loading() {
  return (
    <div className="space-y-8">
      <LoadingSkeleton variant="text" />
      <LoadingSkeleton variant="card" count={2} />
      <LoadingSkeleton variant="evidence" count={5} />
    </div>
  );
}
