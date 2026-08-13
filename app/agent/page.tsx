import { AgentHealthCard } from "@/components/agent/agent-health-card";
import { AgentRunTimeline } from "@/components/agent/agent-run-timeline";
import { RecommendationCard } from "@/components/agent/recommendation-card";
import { EmptyState } from "@/components/common/empty-state";
import { PageHeader } from "@/components/layout/page-header";
import {
  getActionFor,
  getAgentHealth,
  getDataFreshness,
  getLatestAgentRun,
  getRecommendations,
  parseScenario,
} from "@/lib/data";

/** STAFFI 활동 — 에이전트가 언제 무엇을 했고, 무엇을 추천했는지 */
export default async function AgentPage({ searchParams }: { searchParams: { scenario?: string } }) {
  const scenario = parseScenario(searchParams.scenario);
  const [run, recommendations, health, freshness] = await Promise.all([
    getLatestAgentRun(),
    getRecommendations(scenario),
    getAgentHealth(),
    getDataFreshness(scenario),
  ]);

  const actions = await Promise.all(recommendations.map((r) => getActionFor(r.id)));

  return (
    <>
      <PageHeader
        title="STAFFI 활동"
        description="사장님이 열어보지 않아도 STAFFI는 매주 월요일 아침에 일합니다."
      />

      <AgentRunTimeline run={run} />

      <section className="space-y-4" aria-label="행동 추천">
        <div className="space-y-1">
          <h2 className="text-2xl font-bold">그래서 지금 하실 일</h2>
          <p className="text-base text-muted-foreground">
            하시겠다·안 하시겠다를 눌러주시면 다음 추천이 더 맞아집니다.
          </p>
        </div>

        {recommendations.length === 0 ? (
          <EmptyState
            title="아직 드릴 추천이 없습니다"
            description="데이터가 더 쌓이면 무엇을 하면 좋을지 알려드리겠습니다."
          />
        ) : (
          <div className="space-y-4">
            {recommendations.map((r, i) => (
              <RecommendationCard
                key={r.id}
                recommendation={r}
                action={actions[i]}
                defaultOpen={i === 0}
              />
            ))}
          </div>
        )}
      </section>

      <AgentHealthCard health={health} freshness={freshness} />
    </>
  );
}
