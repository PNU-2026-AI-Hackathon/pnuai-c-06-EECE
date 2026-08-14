import { ChangeIndicator } from "@/components/common/change-indicator";
import { ChartFrame } from "@/components/common/chart-frame";
import { EvidenceList } from "@/components/common/evidence-list";
import { MetricCard } from "@/components/common/metric-card";
import { MockDataBadge } from "@/components/common/data-origin-badge";

/** 프리뷰용 고정 값 — 목 데이터 파일과 연결하지 않고 이 자리에서만 쓴다 */
const SAMPLE_EVIDENCE = [
  {
    label: "중간고사 기간 체류시간 증가",
    contribution: 9,
    source: "매장 데이터 12주",
    detail: "지난 두 학기 시험 기간에 오후 2~6시 매출이 평균 21% 늘었습니다.",
  },
  { label: "시험 기간 재방문 증가", contribution: 5, source: "매장 데이터 33주" },
  { label: "수요일 강수 예보", contribution: -3, source: "기상청 중기예보" },
  { label: "시험 종료 후 주말 이탈 완화", contribution: 2, source: "매장 데이터 12주" },
];

const SAMPLE_BARS = [
  { label: "월", value: 560000 },
  { label: "화", value: 588000 },
  { label: "수", value: 455000 },
  { label: "목", value: 642000 },
  { label: "금", value: 612000 },
  { label: "토", value: 404000 },
  { label: "일", value: 0 },
];

/** 지표·근거·차트 관련 공통 컴포넌트 프리뷰 */
export function PreviewMetrics() {
  const max = Math.max(...SAMPLE_BARS.map((b) => b.value));

  return (
    <div className="space-y-12">
      <section className="space-y-4">
        <h2 className="text-2xl font-bold">MockDataBadge</h2>
        <div className="flex flex-wrap items-center gap-4">
          <MockDataBadge />
          <MockDataBadge size="lg" />
          <MockDataBadge label="예시 데이터 · 실제 매출 아님" />
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-2xl font-bold">ChangeIndicator</h2>
        <p className="text-muted-foreground">색 + 화살표 + 부호를 항상 함께 씁니다.</p>
        <div className="flex flex-wrap items-center gap-4">
          <ChangeIndicator value={5.6} />
          <ChangeIndicator value={-12.4} />
          <ChangeIndicator value={0} />
          <ChangeIndicator value={18} size="lg" />
          <ChangeIndicator value={-14} unit="%p" comparedTo="예측값" size="lg" />
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-2xl font-bold">MetricCard</h2>
        <div className="grid gap-5 md:grid-cols-2">
          <MetricCard
            label="이번 주 총매출"
            value="326만원"
            change={5.6}
            note="10월 12일 ~ 18일 · 일요일 휴무 제외"
            emphasis="lg"
          />
          <MetricCard
            label="다음 주 예상 매출"
            value="368만원"
            change={13}
            comparedTo="이번 주"
            origin="sample"
            note="중간고사 주 (10월 19일 ~ 25일)"
          />
          <MetricCard label="가장 많이 팔린 메뉴" value="아이스 아메리카노" note="318잔 · 전체의 39%" />
          <MetricCard
            label="지난주 예측 오차"
            value="14"
            unit="%p"
            change={-14}
            comparedTo="예측값"
            changeUnit="%p"
            note="비 예보를 반영하지 못했습니다"
          />
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-2xl font-bold">MetricCard + EvidenceList</h2>
        <p className="text-muted-foreground">예측 수치에는 근거를 반드시 붙입니다 (설계 원칙 1).</p>
        <MetricCard
          label="다음 주 예상 증감률"
          value="+13%"
          origin="sample"
          emphasis="lg"
          note="2026년 10월 4주차 (중간고사)"
          evidence={<EvidenceList items={SAMPLE_EVIDENCE} total={13} />}
        />
      </section>

      <section className="space-y-4">
        <h2 className="text-2xl font-bold">ChartFrame</h2>
        <p className="text-muted-foreground">
          차트에는 요약 문장(aria-label)과 같은 데이터의 표가 항상 따라붙습니다.
        </p>
        <ChartFrame
          title="요일별 매출"
          description="10월 12일 ~ 18일"
          origin="sample"
          summary="요일별 매출입니다. 목요일이 64만 2천원으로 가장 높고, 토요일이 40만 4천원으로 가장 낮으며, 일요일은 휴무로 매출이 없습니다."
          table={{
            headers: ["요일", "매출"],
            rows: SAMPLE_BARS.map((b) => [b.label, b.value === 0 ? "휴무" : `${b.value.toLocaleString("ko-KR")}원`]),
          }}
          tableMode="visible"
        >
          <div className="flex h-52 items-end gap-3 pt-2">
            {SAMPLE_BARS.map((b) => (
              <div key={b.label} className="flex flex-1 flex-col items-center gap-2">
                <div
                  className="w-full rounded-t-md bg-primary"
                  style={{ height: `${Math.max((b.value / max) * 100, 2)}%` }}
                />
                <span className="text-base font-medium text-muted-foreground">{b.label}</span>
              </div>
            ))}
          </div>
        </ChartFrame>
      </section>
    </div>
  );
}
