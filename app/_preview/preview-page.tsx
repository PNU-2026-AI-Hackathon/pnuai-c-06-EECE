import { notFound } from "next/navigation";

import { PageHeader } from "@/components/layout/page-header";

import { PreviewMetrics } from "./preview-metrics";
import { PreviewStates } from "./preview-states";

/**
 * 공통 컴포넌트 프리뷰 (Storybook 대체).
 * app/_preview 는 Next.js 규칙상 라우팅되지 않는 비공개 폴더라, app/preview/page.tsx 가 이 컴포넌트를 노출한다.
 * 프로덕션 빌드에서는 404를 반환한다.
 */
export function PreviewPage() {
  if (process.env.NODE_ENV === "production") notFound();

  return (
    <div className="space-y-14">
      <PageHeader
        title="공통 컴포넌트"
        description="데이터 연결 전, 레이아웃과 공통 컴포넌트의 모양·접근성을 확인하는 개발용 화면입니다."
      />

      <section className="space-y-3 rounded-xl border bg-card p-6">
        <h2 className="text-xl font-bold">확인 방법</h2>
        <ul className="list-disc space-y-1 pl-5 text-base text-muted-foreground">
          <li>Tab 키만으로 사이드바 메뉴와 버튼을 모두 지날 수 있는지 (포커스 테두리가 보여야 함)</li>
          <li>브라우저를 흑백으로 봐도 증가·감소가 구분되는지 (화살표와 부호로 구분)</li>
          <li>브라우저 확대 200%에서 글자가 잘리지 않는지</li>
          <li>차트를 스크린리더로 읽었을 때 요약 문장과 표가 읽히는지</li>
        </ul>
      </section>

      <PreviewMetrics />
      <PreviewStates />
    </div>
  );
}
