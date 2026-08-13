import { LoadingSkeleton } from "@/components/common/loading-skeleton";

/** 홈 로딩 상태 — 실제 배치와 같은 순서로 자리를 잡아둔다 */
export default function Loading() {
  return (
    <div className="space-y-8">
      <LoadingSkeleton variant="text" />
      <div className="grid gap-5 md:grid-cols-2">
        <LoadingSkeleton variant="card" />
        <LoadingSkeleton variant="card" />
      </div>
      <LoadingSkeleton variant="evidence" count={3} />
    </div>
  );
}
