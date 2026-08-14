import { ContentPlan } from "@/components/content/content-plan";
import { PageHeader } from "@/components/layout/page-header";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { getContent, parseScenario } from "@/lib/data";

/**
 * 홍보 콘텐츠 — 예측을 릴스 대본과 게시글로 옮긴 결과.
 * 생성 엔진(LLM)과 게시 연동이 아직 없어, 사람이 만든 예시 한 벌을 그대로 보여준다.
 */
export default async function ContentPage({
  searchParams,
}: {
  searchParams: { scenario?: string };
}) {
  const scenario = parseScenario(searchParams.scenario);
  const content = await getContent(scenario);

  return (
    <>
      <PageHeader
        title="홍보 콘텐츠"
        description="다음 주 예측을 릴스 대본과 게시글로 옮겨드립니다."
        origin={content.origin}
      />

      <Alert>
        <AlertTitle className="text-base font-bold">아직 사람이 만든 예시입니다</AlertTitle>
        <AlertDescription className="text-base leading-relaxed">
          완성됐을 때 무엇을 받아 보시게 되는지 보여드리는 화면입니다. 매장 데이터로 콘텐츠를 자동으로
          만드는 기능과 인스타그램 게시 연동은 아직 준비 중입니다.
        </AlertDescription>
      </Alert>

      <ContentPlan content={content} />
    </>
  );
}
