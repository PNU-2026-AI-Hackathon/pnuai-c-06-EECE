import { ChartFrame } from "@/components/common/chart-frame";
import { EmptyState } from "@/components/common/empty-state";
import { MetricCard } from "@/components/common/metric-card";
import { HourlyRevenueChart } from "@/components/charts/hourly-revenue-chart";
import { WeekdayRevenueChart } from "@/components/charts/weekday-revenue-chart";
import { PageHeader } from "@/components/layout/page-header";
import { MissedOpportunityCard } from "@/components/missed/missed-opportunity-card";
import { MenuSalesTable } from "@/components/weekly/menu-sales-table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  getMissedOpportunities,
  getMissedOpportunityLimitation,
  getWeeklyAnalysis,
  parseScenario,
} from "@/lib/data";
import { formatPeriod, formatWon, formatWonShort, weekdayLabel } from "@/lib/format";

/** 주간 리포트 — 지난주에 무슨 일이 있었는지 */
export default async function WeeklyPage({ searchParams }: { searchParams: { scenario?: string } }) {
  const scenario = parseScenario(searchParams.scenario);
  const [analysis, missed, missedLimitation] = await Promise.all([
    getWeeklyAnalysis(scenario),
    getMissedOpportunities(scenario),
    getMissedOpportunityLimitation(scenario),
  ]);

  const isMock = analysis.origin === "sample";
  const openDays = analysis.weekdaySales.filter((d) => d.revenue > 0);
  const dailyAverage = Math.round(analysis.totalRevenue / Math.max(openDays.length, 1));
  const busiest = [...analysis.weekdaySales].sort((a, b) => b.revenue - a.revenue)[0];
  const peakHour = [...analysis.hourlySales].sort((a, b) => b.revenue - a.revenue)[0];
  const totalItems = analysis.weekdaySales.reduce((s, d) => s + d.orderCount, 0);

  return (
    <>
      <PageHeader
        title="주간 리포트"
        description={`${formatPeriod(analysis.period.start, analysis.period.end)} · 영업 ${openDays.length}일`}
        isMockData={isMock}
      />

      <section className="grid gap-5 md:grid-cols-3" aria-label="주간 요약">
        <MetricCard
          label="총매출"
          value={formatWonShort(analysis.totalRevenue)}
          change={analysis.changeRateVsPrevWeek}
          note={formatWon(analysis.totalRevenue)}
        />
        <MetricCard
          label="영업일 하루 평균"
          value={formatWonShort(dailyAverage)}
          note={`${openDays.length}일 기준 · 판매 ${totalItems.toLocaleString("ko-KR")}개`}
        />
        <MetricCard
          label="가장 바쁜 날"
          value={`${weekdayLabel(busiest.weekday)}요일`}
          note={`${formatWon(busiest.revenue)} · ${busiest.orderCount}개 판매`}
        />
      </section>

      <ChartFrame
        title="요일별 매출"
        description="일요일은 정기 휴무입니다"
        isMockData={isMock}
        summary={`요일별 매출입니다. ${weekdayLabel(busiest.weekday)}요일이 ${formatWonShort(
          busiest.revenue
        )}으로 가장 높고, 일요일은 휴무로 매출이 없습니다.`}
        table={{
          headers: ["요일", "매출", "판매 수량"],
          rows: analysis.weekdaySales.map((d) => [
            `${weekdayLabel(d.weekday)}요일`,
            d.revenue === 0 ? "휴무" : formatWon(d.revenue),
            d.revenue === 0 ? "—" : `${d.orderCount}개`,
          ]),
        }}
      >
        <WeekdayRevenueChart data={analysis.weekdaySales} />
      </ChartFrame>

      {peakHour ? (
        <ChartFrame
          title="시간대별 매출"
          description={`가장 붐비는 시간은 ${peakHour.hour}시입니다`}
          isMockData={isMock}
          summary={`시간대별 매출입니다. ${peakHour.hour}시가 ${formatWonShort(
            peakHour.revenue
          )}으로 가장 높습니다.`}
          table={{
            headers: ["시간", "매출", "판매 수량"],
            rows: analysis.hourlySales.map((h) => [`${h.hour}시`, formatWon(h.revenue), `${h.orderCount}개`]),
          }}
        >
          <HourlyRevenueChart data={analysis.hourlySales} />
        </ChartFrame>
      ) : (
        <Card className="shadow-none">
          <CardHeader className="pb-2">
            <CardTitle className="text-xl">시간대별 매출</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-base text-muted-foreground">
              올려주신 파일에 결제 시각이 없어 시간대별 매출은 만들 수 없습니다. 추측한 숫자 대신 비워 둡니다.
              POS에서 시각이 포함된 파일을 내려받아 올리시면 바로 채워 드립니다.
            </p>
          </CardContent>
        </Card>
      )}

      <MenuSalesTable menus={analysis.topMenus} isMockData={isMock} />

      <section className="space-y-4" aria-label="놓친 기회">
        <h2 className="text-2xl font-bold">놓친 판매 기회 {missed.length > 0 && `${missed.length}건`}</h2>
        {missed.length === 0 ? (
          <EmptyState
            title="놓친 기회를 판단할 수 없습니다"
            description={
              missedLimitation ??
              "품절로 판단할 만한 패턴이 아직 없습니다. 데이터가 더 쌓이면 다시 확인해 드립니다."
            }
          />
        ) : (
          <div className="space-y-4">
            {missed.map((m) => (
              <MissedOpportunityCard key={m.id} item={m} isMockData={m.origin === "sample"} />
            ))}
          </div>
        )}
      </section>
    </>
  );
}
