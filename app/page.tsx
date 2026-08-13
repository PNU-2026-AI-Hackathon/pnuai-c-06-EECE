import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { DataInsufficientNotice } from "@/components/common/data-insufficient-notice";
import { EvidenceList } from "@/components/common/evidence-list";
import { MetricCard } from "@/components/common/metric-card";
import { AcademicEventList } from "@/components/forecast/academic-event-list";
import { VerificationCard } from "@/components/forecast/verification-card";
import { PageHeader } from "@/components/layout/page-header";
import { MissedOpportunityCard } from "@/components/missed/missed-opportunity-card";
import { Button } from "@/components/ui/button";
import {
  getForecast,
  getLatestVerification,
  getMissedOpportunities,
  getStore,
  getWeeklyAnalysis,
  parseScenario,
} from "@/lib/data";
import { formatChangeRate, formatPeriod, formatWon, formatWonShort } from "@/lib/format";

/** 홈 — 사장님이 오늘 봐야 할 것만 위에서부터 순서대로 */
export default async function HomePage({
  searchParams,
}: {
  searchParams: { scenario?: string };
}) {
  const scenario = parseScenario(searchParams.scenario);
  const [store, analysis, forecast, missed, verification] = await Promise.all([
    getStore(scenario),
    getWeeklyAnalysis(scenario),
    getForecast(scenario),
    getMissedOpportunities(scenario),
    getLatestVerification(scenario),
  ]);

  const isMock = analysis.origin === "sample";
  const topMissed = missed[0];
  const canForecast = forecast.expectedChangeRate !== null;

  return (
    <>
      <PageHeader
        title={`${store.name} 사장님`}
        description={`${formatPeriod(analysis.period.start, analysis.period.end)} 매출을 정리하고, 다음 주를 미리 봤습니다.`}
        isMockData={isMock}
      />

      <section className="grid gap-5 md:grid-cols-2" aria-label="핵심 지표">
        <MetricCard
          label="지난주 총매출"
          value={formatWonShort(analysis.totalRevenue)}
          change={analysis.changeRateVsPrevWeek}
          note={`${formatWon(analysis.totalRevenue)} · 일요일 휴무 제외`}
          emphasis="lg"
        />

        {canForecast ? (
          <MetricCard
            label={`다음 주 예상 (${forecast.targetWeekLabel})`}
            value={formatChangeRate(forecast.expectedChangeRate!)}
            change={forecast.expectedChangeRate!}
            comparedTo="이번 주"
            note={forecast.dataSufficiency.message}
            emphasis="lg"
          />
        ) : (
          <DataInsufficientNotice sufficiency={forecast.dataSufficiency} />
        )}
      </section>

      {canForecast && (
        <section className="space-y-4" aria-label="예측 근거">
          <div className="rounded-xl border bg-card p-6">
            <EvidenceList items={forecast.evidence.slice(0, 3)} caption="이렇게 본 이유" />
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

      {topMissed && (
        <section className="space-y-4" aria-label="놓친 기회">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-2xl font-bold">이번 주에 놓친 매출</h2>
            <Button asChild variant="ghost" size="lg">
              <Link href="/weekly">
                {missed.length}건 모두 보기
                <ArrowRight aria-hidden className="ml-2 size-4" />
              </Link>
            </Button>
          </div>
          <MissedOpportunityCard item={topMissed} isMockData={topMissed.origin === "sample"} />
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
          <VerificationCard verification={verification} isMockData={verification.origin === "sample"} compact />
        </section>
      )}
    </>
  );
}
