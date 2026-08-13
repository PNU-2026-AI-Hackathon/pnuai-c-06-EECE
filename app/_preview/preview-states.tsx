import { FileSpreadsheet, Megaphone } from "lucide-react";

import { DataInsufficientNotice } from "@/components/common/data-insufficient-notice";
import { EmptyState } from "@/components/common/empty-state";
import { LoadingSkeleton } from "@/components/common/loading-skeleton";
import { Button } from "@/components/ui/button";

/** 부족·없음·로딩 상태 컴포넌트 프리뷰 */
export function PreviewStates() {
  return (
    <div className="space-y-12">
      <section className="space-y-4">
        <h2 className="text-2xl font-bold">DataInsufficientNotice</h2>
        <p className="text-muted-foreground">
          데이터가 모자라면 추측한 숫자 대신 이 안내를 보여줍니다 (설계 원칙 2).
        </p>
        <DataInsufficientNotice
          sufficiency={{
            level: "insufficient",
            message:
              "매출 데이터가 3주치뿐이라 다음 주 예측을 만들 수 없습니다. 5주치가 더 쌓이면 예측을 시작합니다. 그때까지는 학사일정만 안내해 드릴게요.",
            weeksAvailable: 3,
            weeksRequired: 8,
          }}
        />
        <DataInsufficientNotice
          sufficiency={{
            level: "limited",
            message: "축제 기간 데이터가 작년 한 번뿐이라 오차가 클 수 있습니다. 참고용으로만 봐주세요.",
            weeksAvailable: 33,
            weeksRequired: 8,
          }}
        />
      </section>

      <section className="space-y-4">
        <h2 className="text-2xl font-bold">EmptyState</h2>
        <EmptyState
          icon={FileSpreadsheet}
          title="아직 올린 매출 파일이 없습니다"
          description="POS에서 내려받은 매출 파일(CSV)을 한 번만 올리면, 다음부터는 사장님이 하실 일이 없습니다."
          action={<Button size="lg">매출 파일 올리기</Button>}
        />
        <EmptyState
          icon={Megaphone}
          title="만든 홍보 콘텐츠가 없습니다"
          description="다음 주 예측을 바탕으로 릴스 대본과 게시글을 만들어 드립니다."
          action={<Button size="lg">콘텐츠 만들어보기</Button>}
        />
      </section>

      <section className="space-y-4">
        <h2 className="text-2xl font-bold">LoadingSkeleton</h2>
        <div className="space-y-6">
          <div className="space-y-2">
            <p className="font-semibold text-muted-foreground">variant=&quot;metric&quot; · count=3</p>
            <LoadingSkeleton variant="metric" count={3} />
          </div>
          <div className="space-y-2">
            <p className="font-semibold text-muted-foreground">variant=&quot;chart&quot;</p>
            <LoadingSkeleton variant="chart" />
          </div>
          <div className="space-y-2">
            <p className="font-semibold text-muted-foreground">variant=&quot;table&quot;</p>
            <LoadingSkeleton variant="table" />
          </div>
          <div className="space-y-2">
            <p className="font-semibold text-muted-foreground">variant=&quot;evidence&quot; · count=3</p>
            <LoadingSkeleton variant="evidence" count={3} />
          </div>
        </div>
      </section>
    </div>
  );
}
