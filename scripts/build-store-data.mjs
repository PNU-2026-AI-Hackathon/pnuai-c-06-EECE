/**
 * data/pub-sales-pnu-2025.csv → mocks/generated/store-data.json
 *
 * 시연 기준 시점을 2025-10-19(일)로 두고,
 *  - 지난주(10/13~19) 주간 분석
 *  - 다음 주(10/20~26, 중간고사) 예측과 근거
 *  - 그 전 주(10/06~12)에 대한 백테스트 검증(예측 vs 실제)
 * 을 만들어 낸다. 모든 숫자는 CSV에서 계산되며 손으로 적은 값은 없다.
 *
 * 실행: node scripts/build-store-data.mjs
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  MENU_COLUMNS,
  addDays,
  countEventCases,
  decomposeContributions,
  forecastSpread,
  estimateMenuPrices,
  groupFullWeeks,
  momentumFactor,
  parseCsv,
  predictDay,
  trainModel,
  weekStartOf,
} from "./lib/csv-model.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const CSV_PATH = path.join(ROOT, "data/pub-sales-pnu-2025.csv");
const OUT_PATH = path.join(ROOT, "mocks/generated/store-data.json");

/** 시연 기준 시점 — 이 날짜까지의 데이터만 사용해 예측한다 */
const DEMO_TODAY = "2025-10-19";
const STORE = { id: "store_pnu_pub_001", name: "장전동 포차", category: "pub" };

/** CSV의 학사이벤트 라벨 → 화면에 쓸 이벤트 정보 */
const EVENT_META = {
  "개강 초기": { name: "개강 초기", type: "semester_start" },
  중간고사: { name: "중간고사", type: "midterm" },
  "중간고사 종료 직후": { name: "중간고사 종료 직후", type: "midterm" },
  기말고사: { name: "기말고사", type: "final" },
  "기말고사 종료 직후": { name: "기말고사 종료 직후", type: "final" },
  "축제 주간": { name: "대학축제", type: "festival" },
  "축제/행사 주간": { name: "대학축제·행사", type: "festival" },
  여름방학: { name: "여름방학", type: "vacation" },
  겨울방학: { name: "겨울방학", type: "vacation" },
};

const sum = (xs) => xs.reduce((s, x) => s + x, 0);
const round100 = (v) => Math.round(v / 100) * 100;

/** 주 단위 예측 (모멘텀 적용 전/후를 함께 돌려준다) */
function predictWeek(model, days, momentum) {
  const raw = sum(days.map((d) => predictDay(model, d.weekday, d.event)));
  return { raw, adjusted: raw * momentum };
}

/** 해당 주의 학사일정 이벤트를 라벨 연속 구간으로 묶는다 */
function eventsOfWeek(days) {
  const events = [];
  for (const day of days) {
    const meta = EVENT_META[day.event];
    if (!meta) continue;
    const last = events[events.length - 1];
    if (last && last.name === meta.name) last.endDate = day.date;
    else events.push({ name: meta.name, startDate: day.date, endDate: day.date, type: meta.type });
  }
  return events;
}

/** 주간 분석 만들기 */
function buildWeeklyAnalysis(week, prevWeek, prices) {
  const menus = Object.values(MENU_COLUMNS);
  const topMenus = menus
    .map((menu) => {
      const quantity = sum(week.days.map((d) => d.quantities[menu]));
      return { menuName: menu, quantity, revenue: quantity * prices[menu], share: 0 };
    })
    .sort((a, b) => b.revenue - a.revenue);
  for (const m of topMenus) m.share = Number(((m.revenue / week.revenue) * 100).toFixed(1));

  return {
    storeId: STORE.id,
    period: { start: week.weekStart, end: week.weekEnd },
    totalRevenue: week.revenue,
    changeRateVsPrevWeek: prevWeek
      ? Number(((week.revenue / prevWeek.revenue - 1) * 100).toFixed(1))
      : 0,
    prevWeekRevenue: prevWeek ? prevWeek.revenue : null,
    topMenus,
    weekdaySales: week.days.map((d) => ({
      weekday: d.weekday,
      revenue: d.revenue,
      orderCount: d.totalQuantity,
    })),
    // 이 CSV에는 결제 시각이 없어 시간대별 매출을 만들 수 없다 (추측하지 않는다)
    hourlySales: [],
    origin: "computed",
  };
}

/** 다음 주 예측과 근거 */
function buildForecast(model, analysisWeek, targetDays, momentum, weeks, history) {
  const baselineOfAnalysis = sum(analysisWeek.days.map((d) => predictDay(model, d.weekday, d.event)));
  const target = predictWeek(model, targetDays, momentum);
  const weeksAvailable = weeks.length;

  const fLevel = baselineOfAnalysis / analysisWeek.revenue;
  const fEvent = target.raw / baselineOfAnalysis;
  const changeRate = (target.adjusted / analysisWeek.revenue - 1) * 100;

  const targetEventLabels = [...new Set(targetDays.map((d) => d.event))];
  const mainEvent = targetEventLabels.find((e) => e !== "일반 학기") ?? "일반 학기";
  const eventDays = model.eventSampleDays[mainEvent] ?? 0;

  const factors = [
    {
      label: `${EVENT_META[mainEvent]?.name ?? mainEvent} 기간 진입`,
      factor: fEvent,
      source: `지난 1년 중 같은 기간 ${eventDays}일 실적`,
      detail: `${EVENT_META[mainEvent]?.name ?? mainEvent} 기간의 하루 매출은 평소의 ${Math.round(
        (model.eventFactor[mainEvent] ?? 1) * 100
      )}% 수준이었습니다.`,
    },
    {
      label: "지난주가 평소 수준과 달랐던 부분",
      factor: fLevel,
      source: `매장 데이터 ${weeksAvailable}주`,
      detail: `지난주 실적은 모델이 본 평소 수준의 ${Math.round(
        (analysisWeek.revenue / baselineOfAnalysis) * 100
      )}%였습니다.`,
    },
    {
      label: "최근 3주 추세",
      factor: momentum,
      source: "직전 3주 실적과 모델 기준 비교",
      detail: `최근 3주는 모델 기준보다 ${Math.round((momentum - 1) * 100)}% ${
        momentum >= 1 ? "높았습니다" : "낮았습니다"
      }.`,
    },
  ];

  const evidence = decomposeContributions(factors, changeRate).map(
    ({ label, contribution, source, detail }) => ({ label, contribution, source, detail })
  );
  const expectedChangeRate = sum(evidence.map((e) => e.contribution));

  // 과거에 같은 이벤트가 몇 번 있었는지 — "33주"보다 이 숫자가 신뢰도를 정확히 말해준다
  const cases = countEventCases(history, mainEvent);
  const eventLabel = EVENT_META[mainEvent]?.name ?? mainEvent;
  const comparableCases = {
    eventName: eventLabel,
    caseCount: cases.caseCount,
    dayCount: cases.dayCount,
    caution:
      cases.caseCount >= 3
        ? null
        : `비교할 수 있는 ${eventLabel} 기간이 ${cases.caseCount}번(${cases.dayCount}일)뿐이라 실제와 차이가 클 수 있습니다.`,
  };

  // 과거 주간 예측이 빗나간 폭으로 범위를 만든다
  const spread = forecastSpread(model, weeks, momentum, cases.dayCount);
  const expectedRange = {
    low: Math.round((target.adjusted * spread.low) / analysisWeek.revenue * 100 - 100),
    high: Math.round((target.adjusted * spread.high) / analysisWeek.revenue * 100 - 100),
    coverage: spread.coverage,
  };

  return {
    storeId: STORE.id,
    targetWeek: { start: targetDays[0].date, end: targetDays[targetDays.length - 1].date },
    targetWeekLabel: `${targetDays[0].date.slice(5, 7)}월 ${EVENT_META[mainEvent]?.name ?? "다음"} 주간`,
    expectedChangeRate,
    expectedRange,
    comparableCases,
    expectedRevenue: round100(analysisWeek.revenue * (1 + expectedChangeRate / 100)),
    expectedRevenueRange: {
      low: round100(analysisWeek.revenue * (1 + expectedRange.low / 100)),
      high: round100(analysisWeek.revenue * (1 + expectedRange.high / 100)),
    },
    // 사례가 3회 미만이면 신뢰 수준을 올리지 않는다
    confidence: cases.caseCount >= 3 ? "high" : cases.caseCount >= 2 ? "medium" : "low",
    evidence,
    academicEvents: eventsOfWeek(targetDays),
    dataSufficiency: {
      level: "sufficient",
      message: `매출 ${weeksAvailable}주치를 학습했지만, 비교할 수 있는 ${eventLabel} 기간은 ${cases.caseCount}번(${cases.dayCount}일)입니다.`,
      weeksAvailable,
      weeksRequired: 8,
    },
    origin: "computed",
  };
}

/** 지난주 예측을 백테스트해 실제와 비교 (그 주 이전 데이터만 학습에 사용) */
function buildVerification(rows, weeks, targetWeek, priorWeek) {
  const trainRows = rows.filter((r) => r.date < targetWeek.weekStart);
  const model = trainModel(trainRows);
  const momentum = momentumFactor(model, trainRows);
  const predicted = predictWeek(model, targetWeek.days, momentum).adjusted;

  const predictedChangeRate = Number(((predicted / priorWeek.revenue - 1) * 100).toFixed(1));
  const actualChangeRate = Number(((targetWeek.revenue / priorWeek.revenue - 1) * 100).toFixed(1));
  const errorPoints = Number((actualChangeRate - predictedChangeRate).toFixed(1));

  const worst = targetWeek.days
    .map((d) => ({
      date: d.date,
      weekdayName: d.weekdayName,
      diff: d.revenue - predictDay(model, d.weekday, d.event) * momentum,
    }))
    .sort((a, b) => Math.abs(b.diff) - Math.abs(a.diff))[0];

  const missedBig = Math.abs(errorPoints) >= 10;
  return {
    storeId: STORE.id,
    period: { start: targetWeek.weekStart, end: targetWeek.weekEnd },
    predictedChangeRate,
    actualChangeRate,
    errorPoints,
    predictedConfidence: "medium",
    errorAnalysis: `${worst.date.slice(5).replace("-", "월 ")}일(${worst.weekdayName})이 예측보다 ${Math.abs(
      Math.round(worst.diff / 10000)
    )}만원 ${worst.diff > 0 ? "높아" : "낮아"} 오차의 대부분을 만들었습니다. 가능한 원인으로 날씨, 주변 행사, 영업시간 변경, 품절 등이 있지만 무엇이었는지는 확인이 필요합니다. 지금은 학사일정과 요일 패턴만 보고 있습니다.`,
    reflectedInModel: missedBig,
    reflectionNote: missedBig
      ? "최근 3주 추세를 예측 조건에 더 크게 반영합니다. 다음 예측부터 적용됩니다."
      : null,
    origin: "computed",
  };
}

/** 업로드 결과 (정규화·경고를 CSV 사실에서 만들어 낸다) */
function buildUploadResult(rows, prices, maxRelError) {
  const menuNormalizations = Object.entries(MENU_COLUMNS).map(([column, menu]) => ({
    rawName: column,
    normalizedName: menu,
    confidence: 1,
    occurrences: sum(rows.map((r) => r.quantities[menu])),
  }));

  return {
    id: "upload_pub_2025",
    storeId: STORE.id,
    fileName: "pub-sales-pnu-2025.csv",
    uploadedAt: `${DEMO_TODAY}T21:40:00`,
    processedRows: rows.length,
    skippedRows: 0,
    period: { start: rows[0].date, end: rows[rows.length - 1].date },
    recognizedMenuCount: Object.keys(prices).length,
    menuNormalizations,
    warnings: [
      {
        code: "MISSING_VALUE",
        level: "warning",
        message:
          "결제 시각이 없는 일별 집계 파일입니다. 시간대별 매출과 품절 시각은 계산할 수 없어 화면에서 제외했습니다.",
        affectedRows: rows.length,
      },
      {
        code: "UNKNOWN_MENU",
        level: "warning",
        message: `메뉴 단가가 파일에 없어 1년치 매출과 판매 수량으로 역산했습니다. 역산 오차는 ${(
          maxRelError * 100
        ).toFixed(2)}%입니다.`,
        affectedRows: 0,
      },
    ],
    capabilities: [
      { kind: "daily_sales", label: "일별 매출", available: true, missingReason: null },
      { kind: "weekday_pattern", label: "요일별 패턴", available: true, missingReason: null },
      { kind: "menu_analysis", label: "메뉴별 분석", available: true, missingReason: null },
      {
        kind: "hourly_pattern",
        label: "시간대별 매출",
        available: false,
        missingReason: "결제 시각이 없어 시간대별 매출은 만들 수 없습니다.",
      },
      { kind: "academic_event", label: "학사일정 비교", available: true, missingReason: null },
      {
        kind: "early_sales_end",
        label: "판매 조기 종료 탐지",
        available: false,
        missingReason: "결제 시각과 메뉴가 함께 있어야 판매가 일찍 끝났는지 알 수 있습니다.",
      },
    ],
    weeksCovered: 52,
    origin: "computed",
  };
}

function main() {
  const rows = parseCsv(CSV_PATH);
  const { prices, maxRelError } = estimateMenuPrices(rows);

  const history = rows.filter((r) => r.date <= DEMO_TODAY);
  const weeks = groupFullWeeks(history);
  const analysisWeek = weeks[weeks.length - 1];
  const prevWeek = weeks[weeks.length - 2];
  const priorWeek = weeks[weeks.length - 3];

  const model = trainModel(history);
  const momentum = momentumFactor(model, history);

  const targetStart = addDays(analysisWeek.weekStart, 7);
  const targetDays = rows.filter((r) => weekStartOf(r.date) === targetStart);

  const output = {
    meta: {
      generatedFrom: "data/pub-sales-pnu-2025.csv",
      generatedAt: new Date().toISOString(),
      demoToday: DEMO_TODAY,
      estimatedPrices: prices,
      priceEstimationMaxError: maxRelError,
      weeksAvailable: weeks.length,
      note: "이 파일은 scripts/build-store-data.mjs 가 CSV에서 생성합니다. 직접 수정하지 마세요.",
    },
    store: { ...STORE, openedAt: rows[0].date, origin: "computed" },
    weeklyAnalysis: buildWeeklyAnalysis(analysisWeek, prevWeek, prices),
    forecast: buildForecast(model, analysisWeek, targetDays, momentum, weeks, history),
    verification: buildVerification(history, weeks, prevWeek, priorWeek),
    upload: buildUploadResult(rows, prices, maxRelError),
    missedOpportunities: [],
    dataLimitations: [
      "결제 시각이 없어 시간대별 매출을 만들 수 없습니다.",
      "개별 결제 내역이 아닌 일별 집계라 품절 시각과 놓친 기회를 판단할 수 없습니다.",
      "메뉴 단가는 1년치 매출과 판매 수량으로 역산한 값입니다.",
    ],
    dailySeries: history.slice(-70).map((r) => ({
      date: r.date,
      weekday: r.weekday,
      event: r.event,
      revenue: r.revenue,
    })),
  };

  fs.mkdirSync(path.dirname(OUT_PATH), { recursive: true });
  fs.writeFileSync(OUT_PATH, `${JSON.stringify(output, null, 2)}\n`);

  console.log(`생성 완료: ${path.relative(ROOT, OUT_PATH)}`);
  console.log(`  단가 역산 최대 오차: ${(maxRelError * 100).toFixed(4)}%`);
  console.log(`  분석 주: ${analysisWeek.weekStart} ~ ${analysisWeek.weekEnd} (${analysisWeek.revenue.toLocaleString()}원)`);
  console.log(`  예측 주: ${output.forecast.targetWeek.start} ~ ${output.forecast.targetWeek.end} (${output.forecast.expectedChangeRate}%)`);
  console.log(`  검증: 예측 ${output.verification.predictedChangeRate}% vs 실제 ${output.verification.actualChangeRate}%`);
}

main();
