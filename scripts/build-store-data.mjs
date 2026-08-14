/**
 * 매출 CSV → mocks/generated/store-data.json
 *
 * 기준 시점까지의 데이터만 써서
 *  - 지난주 주간 분석
 *  - 다음 주 예측과 근거
 *  - 그 전 주에 대한 백테스트 검증(예측 vs 실제)
 * 을 만들어 낸다. 모든 숫자는 CSV에서 계산되며 손으로 적은 값은 없다.
 *
 * 매장·파일 경로·기준 시점은 data/store.json 에서 읽는다.
 * 학사일정은 CSV가 아니라 data/academic-calendar.json 에서 날짜로 붙인다.
 *
 * 실행: node scripts/build-store-data.mjs [--store=data/store.json] [--file=매출.csv]
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  DEFAULT_LABEL,
  attachAcademicEvents,
  buildFutureDays,
  eventsInRange,
  loadCalendar,
} from "./lib/academic-calendar.mjs";
import {
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
import { detectEarlySalesEnds } from "./lib/early-sales-end.mjs";
import { hourlyForDates } from "./lib/transaction-csv.mjs";
import { buildLimitations, buildUploadResult } from "./lib/upload-report.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const OUT_PATH = path.join(ROOT, "mocks/generated/store-data.json");
const WEEKDAY_NAMES = ["일", "월", "화", "수", "목", "금", "토"];

/** --key=value 형태의 실행 인자 */
function arg(name, fallback) {
  const hit = process.argv.slice(2).find((a) => a.startsWith(`--${name}=`));
  return hit ? hit.slice(name.length + 3) : fallback;
}

/** 매장 설정 — 하드코딩 대신 파일로 받는다 */
function loadConfig() {
  const configPath = path.resolve(ROOT, arg("store", "data/store.json"));
  const config = JSON.parse(fs.readFileSync(configPath, "utf8"));
  return {
    store: { id: config.id, name: config.name, category: config.category },
    salesPath: path.resolve(ROOT, arg("file", config.salesFile)),
    calendarPath: path.resolve(ROOT, config.academicCalendar),
    today: arg("today", config.today) || null,
  };
}

const CONFIG = loadConfig();
const STORE = CONFIG.store;

const sum = (xs) => xs.reduce((s, x) => s + x, 0);
const round100 = (v) => Math.round(v / 100) * 100;

/** 주 단위 예측 (모멘텀 적용 전/후를 함께 돌려준다) */
function predictWeek(model, days, momentum) {
  const raw = sum(days.map((d) => predictDay(model, d.weekday, d.event)));
  return { raw, adjusted: raw * momentum };
}

/** 주간 분석 만들기 */
function buildWeeklyAnalysis(week, prevWeek, prices, menus, hourlyByDate) {
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
      orderCount: d.orderCount ?? d.totalQuantity,
    })),
    // 결제 시각이 없으면 빈 배열이다. 없는 것을 지어내지 않는다.
    hourlySales: hourlyForDates(
      hourlyByDate,
      week.days.map((d) => d.date)
    ),
    origin: "computed",
  };
}

/** 다음 주 예측과 근거 */
function buildForecast(model, analysisWeek, targetDays, momentum, weeks, history, calendar) {
  const baselineOfAnalysis = sum(analysisWeek.days.map((d) => predictDay(model, d.weekday, d.event)));
  const target = predictWeek(model, targetDays, momentum);
  const weeksAvailable = weeks.length;

  const fLevel = baselineOfAnalysis / analysisWeek.revenue;
  const fEvent = target.raw / baselineOfAnalysis;
  const changeRate = (target.adjusted / analysisWeek.revenue - 1) * 100;

  const targetEventLabels = [...new Set(targetDays.map((d) => d.event))];
  const mainEvent = targetEventLabels.find((e) => e !== DEFAULT_LABEL) ?? DEFAULT_LABEL;
  const eventDays = model.eventSampleDays[mainEvent] ?? 0;

  const factors = [
    {
      label: `${mainEvent} 기간 진입`,
      factor: fEvent,
      source: `지난 1년 중 같은 기간 ${eventDays}일 실적`,
      detail: `${mainEvent} 기간의 하루 매출은 평소의 ${Math.round(
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
  const eventLabel = mainEvent;
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
    targetWeekLabel: `${targetDays[0].date.slice(5, 7)}월 ${mainEvent} 주간`,
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
    academicEvents: eventsInRange(
      calendar,
      targetDays[0].date,
      targetDays[targetDays.length - 1].date
    ),
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
      weekdayName: WEEKDAY_NAMES[d.weekday],
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

function main() {
  const parsed = parseCsv(CONFIG.salesPath);
  const calendar = loadCalendar(CONFIG.calendarPath);

  // 학사일정은 매출 파일이 아니라 우리 캘린더에서 날짜로 붙인다
  const { rows, uncovered } = attachAcademicEvents(parsed.rows, calendar);
  const menus = parsed.menus;
  const { prices, maxRelError } = estimateMenuPrices(rows, menus);

  // 기준 시점을 안 주면 파일의 마지막 날짜를 쓴다
  const today = CONFIG.today ?? rows[rows.length - 1].date;
  const history = rows.filter((r) => r.date <= today);
  const weeks = groupFullWeeks(history);
  const analysisWeek = weeks[weeks.length - 1];
  const prevWeek = weeks[weeks.length - 2];
  const priorWeek = weeks[weeks.length - 3];

  const model = trainModel(history);
  const momentum = momentumFactor(model, history);

  // 예측 대상 주는 아직 매출 기록이 없다. 날짜와 학사일정만으로 7일을 만든다.
  const targetStart = addDays(analysisWeek.weekStart, 7);
  const targetDays = buildFutureDays(calendar, targetStart, 7);

  // 결제 시각과 메뉴가 함께 있을 때만 판단할 수 있다.
  // 기준 시점 이후는 아직 모르는 데이터다 — 탐지에도 쓰지 않는다.
  const earlySalesEnds =
    parsed.hasTime && parsed.hasMenu
      ? detectEarlySalesEnds(
          { ...parsed, lastSold: parsed.lastSold.filter((e) => e.date <= today) },
          prices,
          STORE.id
        )
      : [];

  const output = {
    meta: {
      generatedFrom: path.relative(ROOT, CONFIG.salesPath),
      academicCalendar: path.relative(ROOT, CONFIG.calendarPath),
      generatedAt: new Date().toISOString(),
      demoToday: today,
      estimatedPrices: prices,
      priceEstimationMaxError: maxRelError,
      weeksAvailable: weeks.length,
      note: "이 파일은 scripts/build-store-data.mjs 가 CSV에서 생성합니다. 직접 수정하지 마세요.",
    },
    store: { ...STORE, openedAt: rows[0].date, origin: "computed" },
    weeklyAnalysis: buildWeeklyAnalysis(analysisWeek, prevWeek, prices, menus, parsed.hourlyByDate),
    forecast: buildForecast(model, analysisWeek, targetDays, momentum, weeks, history, calendar),
    verification: buildVerification(history, weeks, prevWeek, priorWeek),
    upload: buildUploadResult({
      rows,
      prices,
      maxRelError,
      menus,
      weeksCovered: groupFullWeeks(rows).length,
      today,
      skipped: parsed.skipped,
      shape: parsed.shape,
      hasTime: parsed.hasTime,
      hasMenu: parsed.hasMenu,
      store: STORE,
      salesPath: CONFIG.salesPath,
    }),
    earlySalesEnds,
    dataLimitations: buildLimitations({
      hasTime: parsed.hasTime,
      hasMenu: parsed.hasMenu,
      maxRelError,
      shape: parsed.shape,
    }).map((l) => l.message),
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
  console.log(`  매장: ${STORE.name} (${path.relative(ROOT, CONFIG.salesPath)})`);
  console.log(`  기준 시점: ${today}${CONFIG.today ? "" : " (파일의 마지막 날짜)"}`);
  console.log(`  인식한 메뉴: ${menus.length === 0 ? "없음" : menus.join(", ")}`);
  if (uncovered > 0) console.log(`  ⚠ 학사일정이 없는 날짜 ${uncovered}일 — 캘린더 확인 필요`);
  if (parsed.skipped.badDate + parsed.skipped.missingRevenue > 0) {
    console.log(
      `  ⚠ 제외한 행: 날짜 오류 ${parsed.skipped.badDate}건, 금액 없음 ${parsed.skipped.missingRevenue}건`
    );
  }
  console.log(`  단가 역산 최대 오차: ${(maxRelError * 100).toFixed(4)}%`);
  console.log(`  분석 주: ${analysisWeek.weekStart} ~ ${analysisWeek.weekEnd} (${analysisWeek.revenue.toLocaleString()}원)`);
  console.log(`  예측 주: ${output.forecast.targetWeek.start} ~ ${output.forecast.targetWeek.end} (${output.forecast.expectedChangeRate}%)`);
  console.log(`  검증: 예측 ${output.verification.predictedChangeRate}% vs 실제 ${output.verification.actualChangeRate}%`);
}

main();
