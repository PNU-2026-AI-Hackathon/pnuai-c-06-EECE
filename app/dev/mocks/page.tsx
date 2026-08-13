import { notFound } from "next/navigation";

import { MockPreview } from "@/components/dev/mock-preview";
import { Badge } from "@/components/ui/badge";

/**
 * 개발 전용 목 데이터 프리뷰 페이지 (/dev/mocks).
 * 프로덕션 빌드에서는 404를 반환하며, 실제 화면 개발이 끝나면 app/dev 폴더째 삭제한다.
 */
export default function DevMocksPage() {
  if (process.env.NODE_ENV === "production") notFound();

  return (
    <main className="mx-auto max-w-6xl space-y-4 p-6">
      <header className="space-y-1">
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-bold">목 데이터 프리뷰</h1>
          <Badge variant="secondary">개발 전용</Badge>
        </div>
        <p className="text-sm text-muted-foreground">
          mocks/ 의 시나리오를 확인하는 임시 페이지입니다. 사장님 화면 설계와는 무관합니다.
        </p>
      </header>
      <MockPreview />
    </main>
  );
}
