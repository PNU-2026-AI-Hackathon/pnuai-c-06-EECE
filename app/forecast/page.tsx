import { DataInsufficientNotice } from "@/components/common/data-insufficient-notice";
import { EvidenceList } from "@/components/common/evidence-list";
import { AcademicEventList } from "@/components/forecast/academic-event-list";
import { ForecastRangeCard } from "@/components/forecast/forecast-range-card";
import { VerificationCard } from "@/components/forecast/verification-card";
import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getForecast, getLatestVerification, getWeeklyAnalysis, parseScenario } from "@/lib/data";
import { formatChangeRate, formatPeriod } from "@/lib/format";

/** 수요 예측 — 다음 주가 어떻게 달라질지, 그리고 왜 그렇게 봤는지 */
export default async function ForecastPage({ searchParams }: { searchParams: { scenario?: string } }) {
  const scenario = parseScenario(searchParams.scenario);
  const [forecast, analysis, verification] = await Promise.all([
    getForecast(scenario),
    getWeeklyAnalysis(scenario),
    getLatestVerification(scenario),
  ]);

  const isMock = forecast.origin === "sample";
  const rate = forecast.expectedChangeRate;
  const canForecast = rate !== null;

  return (
    <>
      <PageHeader
        title="수요 예측"
        description={`${forecast.targetWeekLabel} · ${formatPeriod(forecast.targetWeek.start, forecast.targetWeek.end)}`}
        isMockData={isMock}
      />

      {canForecast ? (
        <>
          <ForecastRangeCard forecast={forecast} baseRevenue={analysis.totalRevenue} />

          <Card className="shadow-none">
            <CardHeader className="pb-2">
              <CardTitle className="text-xl">왜 이렇게 봤나</CardTitle>
              <p className="text-base text-muted-foreground">
                아래 근거를 더하면 가장 가능성 높은 값 {formatChangeRate(rate)}가 됩니다. 근거 없는 숫자는
                보여드리지 않습니다.
              </p>
            </CardHeader>
            <CardContent>
              <EvidenceList items={forecast.evidence} total={rate} caption="예상 증감률의 근거" />
            </CardContent>
          </Card>
        </>
      ) : (
        <DataInsufficientNotice sufficiency={forecast.dataSufficiency} />
      )}

      <AcademicEventList events={forecast.academicEvents} />

      {verification ? (
        <VerificationCard verification={verification} isMockData={verification.origin === "sample"} />
      ) : (
        <Card className="shadow-none">
          <CardHeader className="pb-2">
            <CardTitle className="text-xl">지난주 예측 검증</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-base text-muted-foreground">
              아직 검증할 예측이 없습니다. 첫 예측이 지나간 다음 주부터, 얼마나 맞았는지 이 자리에 그대로
              보여드립니다.
            </p>
          </CardContent>
        </Card>
      )}
    </>
  );
}
