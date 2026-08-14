import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { DataFreshnessNotice } from "@/components/agent/data-freshness-notice";
import { RecommendationCard } from "@/components/agent/recommendation-card";
import { DataInsufficientNotice } from "@/components/common/data-insufficient-notice";
import { EvidenceList } from "@/components/common/evidence-list";
import { MetricCard } from "@/components/common/metric-card";
import { AcademicEventList } from "@/components/forecast/academic-event-list";
import { ForecastRangeCard } from "@/components/forecast/forecast-range-card";
import { VerificationCard } from "@/components/forecast/verification-card";
import { PageHeader } from "@/components/layout/page-header";
import { EarlySalesEndCard } from "@/components/early-sales-end/early-sales-end-card";
import { Button } from "@/components/ui/button";
import {
  getDataFreshness,
  getForecast,
  getLatestVerification,
  getEarlySalesEnds,
  getRecommendations,
  getStore,
  getWeeklyAnalysis,
  parseScenario,
} from "@/lib/data";
import { formatPeriod, formatWon, formatWonShort, weekdayLabel } from "@/lib/format";

/** 홈 — 사장님이 오늘 봐야 할 것만 위에서부터 순서대로 */
export default async function HomePage({
  searchParams,
}: {
  searchParams: { scenario?: string };
}) {
  const scenario = parseScenario(searchParams.scenario);
  const [store, analysis, forecast, earlyEnds, verification, recommendations, freshness] =
    await Promise.all([
      getStore(scenario),
      getWeeklyAnalysis(scenario),
      getForecast(scenario),
      getEarlySalesEnds(scenario),
      getLatestVerification(scenario),
      getRecommendations(scenario),
      getDataFreshness(scenario),
    ]);

  const topEarlyEnd = earlyEnds.find((e) => e.ownerConfirmation === "unconfirmed");
  // 휴무 안내는 매출이 0인 요일이 실제로 있을 때만 붙인다 — 없는 사실을 적지 않는다
  const closedDays = analysis.weekdaySales.filter((d) => d.revenue === 0);
  const closedNote =
    closedDays.length > 0
      ? ` · ${closedDays.map((d) => `${weekdayLabel(d.weekday)}요일`).join("·")} 휴무 제외`
      : "";
  // 데이터가 오래되면 낡은 기준으로 계산한 예측을 보여주지 않는다
  const canForecast = forecast.expectedChangeRate !== null && !freshness.blocksForecast;
  const topRecommendations = recommendations.slice(0, 2);

  return (
    <>
      <PageHeader
        title={`${store.name} 사장님`}
        description={`${formatPeriod(analysis.period.start, analysis.period.end)} 매출을 정리하고, 다음 주를 미리 봤습니다.`}
        origin={analysis.origin}
      />

      <section className="grid gap-5 md:grid-cols-2" aria-label="핵심 지표">
        <MetricCard
          label="지난주 총매출"
          value={formatWonShort(analysis.totalRevenue)}
          change={analysis.changeRateVsPrevWeek}
          note={`${formatWon(analysis.totalRevenue)}${closedNote}`}
          emphasis="lg"
        />

        {canForecast ? (
          <ForecastRangeCard forecast={forecast} baseRevenue={analysis.totalRevenue} />
        ) : freshness.blocksForecast ? (
          <DataFreshnessNotice freshness={freshness} />
        ) : (
          <DataInsufficientNotice sufficiency={forecast.dataSufficiency} />
        )}
      </section>

      {canForecast && (
        <section className="space-y-4" aria-label="예측 근거">
          <div className="rounded-xl border bg-card p-6">
            {/* 검증은 근거 전체로 하고, 화면에는 위 3건만 보여준다 */}
            <EvidenceList
              items={forecast.evidence}
              total={forecast.expectedChangeRate ?? undefined}
              visibleCount={3}
              caption="이렇게 본 이유"
            />
            <div className="mt-5">
              <Button asChild variant="outline" size="lg">
                <Link href="/forecast">
                  근거 전부 보기
                  <ArrowRight aria-hidden className="ml-2 size-4" />
                </Link>
              </Button>
            </div>
          </div>
        </section>
      )}

      {topRecommendations.length > 0 && (
        <section className="space-y-4" aria-label="지금 하실 일">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-2xl font-bold">그래서 지금 하실 일</h2>
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
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-2xl font-bold">확인해 주실 것</h2>
            <Button asChild variant="ghost" size="lg">
              <Link href="/weekly">
                {earlyEnds.length}건 모두 보기
                <ArrowRight aria-hidden className="ml-2 size-4" />
              </Link>
            </Button>
          </div>
          <EarlySalesEndCard item={topEarlyEnd} />
        </section>
      )}

      {!canForecast && (
        <AcademicEventList
          events={forecast.academicEvents}
          title="예측은 없지만 이 일정은 확실합니다"
        />
      )}

      {verification && (
        <section className="space-y-4" aria-label="지난주 예측 검증">
          <h2 className="text-2xl font-bold">틀린 것도 그대로 보여드립니다</h2>
          <VerificationCard verification={verification} origin={verification.origin} compact />
        </section>
      )}
    </>
  );
}
