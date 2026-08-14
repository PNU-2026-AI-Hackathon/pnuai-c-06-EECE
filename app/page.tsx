import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { DataFreshnessNotice } from "@/components/agent/data-freshness-notice";
import { RecommendationCard } from "@/components/agent/recommendation-card";
import { DataInsufficientNotice } from "@/components/common/data-insufficient-notice";
import { EarlySalesEndCard } from "@/components/early-sales-end/early-sales-end-card";
import { AcademicEventList } from "@/components/forecast/academic-event-list";
import { VerificationCard } from "@/components/forecast/verification-card";
import { ForecastSummary } from "@/components/home/forecast-summary";
import { HomeHeadline } from "@/components/home/home-headline";
import { SemesterRibbon } from "@/components/semester/semester-ribbon";
import { Button } from "@/components/ui/button";
import {
  getDataFreshness,
  getEarlySalesEnds,
  getForecast,
  getLatestVerification,
  getRecommendations,
  getSemesterContext,
  getStore,
  getWeeklyAnalysis,
  parseScenario,
} from "@/lib/data";
import { buildSemesterRibbon } from "@/lib/semester";

/** 홈 — 결론을 먼저 말하고, 근거와 할 일을 아래로 내린다 */
export default async function HomePage({ searchParams }: { searchParams: { scenario?: string } }) {
  const scenario = parseScenario(searchParams.scenario);
  const [store, analysis, forecast, earlyEnds, verification, recommendations, freshness, semester] =
    await Promise.all([
      getStore(scenario),
      getWeeklyAnalysis(scenario),
      getForecast(scenario),
      getEarlySalesEnds(scenario),
      getLatestVerification(scenario),
      getRecommendations(scenario),
      getDataFreshness(scenario),
      getSemesterContext(scenario),
    ]);

  const ribbon = buildSemesterRibbon(semester.events, semester.today, semester.label);
  // 데이터가 오래되면 낡은 기준으로 계산한 예측을 보여주지 않는다
  const canForecast = forecast.expectedChangeRate !== null && !freshness.blocksForecast;
  const topEarlyEnd = earlyEnds.find((e) => e.ownerConfirmation === "unconfirmed");
  const topRecommendations = recommendations.slice(0, 2);

  return (
    <>
      <HomeHeadline store={store} forecast={forecast} ribbon={ribbon} origin={analysis.origin} />

      <SemesterRibbon ribbon={ribbon} />

      {canForecast ? (
        <ForecastSummary forecast={forecast} analysis={analysis} />
      ) : freshness.blocksForecast ? (
        <DataFreshnessNotice freshness={freshness} />
      ) : (
        <DataInsufficientNotice sufficiency={forecast.dataSufficiency} />
      )}

      {topRecommendations.length > 0 && (
        <section className="space-y-4" aria-label="지금 하실 일">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-2xl font-bold tight">그래서 지금 하실 일</h2>
            <Button asChild variant="ghost" size="lg">
              <Link href="/agent">
                {recommendations.length}건 모두 보기
                <ArrowRight aria-hidden className="ml-2 size-4" />
              </Link>
            </Button>
          </div>
          {topRecommendations.map((r) => (
            <RecommendationCard key={r.id} recommendation={r} />
          ))}
        </section>
      )}

      {topEarlyEnd && (
        <section className="space-y-4" aria-label="판매 조기 종료">
          <h2 className="text-2xl font-bold tight">확인해 주실 것</h2>
          <EarlySalesEndCard item={topEarlyEnd} />
        </section>
      )}

      {!canForecast && (
        <AcademicEventList events={forecast.academicEvents} title="예측은 없지만 이 일정은 확실해요" />
      )}

      {verification && (
        <section className="space-y-4" aria-label="지난주 예측 검증">
          <h2 className="text-2xl font-bold tight">틀린 것도 그대로 보여드려요</h2>
          <VerificationCard verification={verification} origin={verification.origin} compact />
        </section>
      )}
    </>
  );
}
