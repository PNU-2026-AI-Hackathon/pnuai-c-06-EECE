/**
 * 매출 CSV 텍스트 하나로 대시보드에 필요한 모든 것을 만든다.
 *
 * 파일을 읽지 않는다. 텍스트만 받는다 — 오프라인 스크립트도, 업로드 API도 같은 함수를 쓴다.
 * 백엔드가 생기면 이 함수가 Python으로 그대로 옮겨간다.
 */

import {
  DEFAULT_LABEL,
  attachAcademicEvents,
  buildFutureDays,
  eventsInRange,
} from "./academic-calendar.mjs";
import {
  addDays,
  countEventCases,
  decomposeContributions,
  estimateMenuPrices,
  forecastSpread,
  groupFullWeeks,
  momentumFactor,
  parseSales,
  predictDay,
  trainModel,
} from "./csv-model.mjs";
import { detectEarlySalesEnds } from "./early-sales-end.mjs";
import { hourlyForDates } from "./transaction-csv.mjs";
import { buildLimitations, buildUploadResult } from "./upload-report.mjs";

const WEEKDAY_NAMES = ["일", "월", "화", "수", "목", "금", "토"];
const sum = (xs) => xs.reduce((s, x) => s + x, 0);
const round100 = (v) => Math.round(v / 100) * 100;

/** 주 단위 예측 (모멘텀 적용 전/후를 함께 돌려준다) */
function predictWeek(model, days, momentum) {
  const raw = sum(days.map((d) => predictDay(model, d.weekday, d.event)));
  return { raw, adjusted: raw * momentum };
}

/** 주간 분석 만들기 */
function buildWeeklyAnalysis(week, prevWeek, prices, menus, hourlyByDate, storeId) {
  const topMenus = menus
    .map((menu) => {
      const quantity = sum(week.days.map((d) => d.quantities[menu]));
      return { menuName: menu, quantity, revenue: quantity * prices[menu], share: 0 };
    })
    .sort((a, b) => b.revenue - a.revenue);
  for (const m of topMenus) m.share = Number(((m.revenue / week.revenue) * 100).toFixed(1));

  return {
    storeId,
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
function buildForecast(model, analysisWeek, targetDays, momentum, weeks, history, calendar, storeId) {
  const baselineOfAnalysis = sum(analysisWeek.days.map((d) => predictDay(model, d.weekday, d.event)));
  const target = predictWeek(model, targetDays, momentum);
  const weeksAvailable = weeks.length;

  const targetEventLabels = [...new Set(targetDays.map((d) => d.event))];
  const mainEvent = targetEventLabels.find((e) => e !== DEFAULT_LABEL) ?? DEFAULT_LABEL;
  const eventDays = model.eventSampleDays[mainEvent] ?? 0;

  // 과거에 같은 이벤트가 몇 번 있었는지 — "33주"보다 이 숫자가 신뢰도를 정확히 말해준다
  const cases = countEventCases(history, mainEvent);

  // 과거 주간 예측이 빗나간 폭. 범위를 만들고, 한쪽으로 치우친 만큼은 예측값 자체를 보정한다.
  const spread = forecastSpread(model, weeks, history, cases.dayCount);
  const calibrated = target.adjusted * spread.median;

  const fLevel = baselineOfAnalysis / analysisWeek.revenue;
  const fEvent = target.raw / baselineOfAnalysis;
  const changeRate = (calibrated / analysisWeek.revenue - 1) * 100;

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

  // 모델이 이 매장에서 꾸준히 한쪽으로 빗나가 왔다면 그만큼을 근거로 드러내 놓고 보정한다.
  // 1%p 미만이면 굳이 사장님께 보여드릴 항목이 아니다.
  if (Math.abs(spread.median - 1) >= 0.01) {
    factors.push({
      label: "지금까지 빗나간 방향 보정",
      factor: spread.median,
      source: `과거 ${weeksAvailable}주 예측과 실제 비교`,
      detail: `이 매장에서는 예측이 실제보다 꾸준히 ${Math.round(
        Math.abs(spread.median - 1) * 100
      )}% ${spread.median > 1 ? "낮았습니다. 그만큼 올려" : "높았습니다. 그만큼 낮춰"} 잡았습니다.`,
    });
  }

  const evidence = decomposeContributions(factors, changeRate).map(
    ({ label, contribution, source, detail }) => ({ label, contribution, source, detail })
  );
  const expectedChangeRate = sum(evidence.map((e) => e.contribution));

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

  // 범위는 보정한 예측을 가운데 두고 만든다. low ≤ median ≤ high 이므로 항상 예측값을 품는다.
  const expectedRange = {
    low: Math.round(((target.adjusted * spread.low) / analysisWeek.revenue) * 100 - 100),
    high: Math.round(((target.adjusted * spread.high) / analysisWeek.revenue) * 100 - 100),
    coverage: spread.coverage,
  };

  return {
    storeId,
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
function buildVerification(rows, weeks, targetWeek, priorWeek, storeId) {
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
    storeId,
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


/**
 * 매출 CSV 텍스트 → 화면에 필요한 모든 것.
 *
 * @param {object} input
 * @param {string} input.csvText     매출 CSV 원문
 * @param {string} input.fileName    사장님께 보여줄 파일 이름
 * @param {object} input.calendar    학사일정 (data/academic-calendar.json 형태)
 * @param {object} input.store       { id, name, category }
 * @param {string|null} input.today  기준 시점. null이면 파일의 마지막 날짜
 */
export function analyzeSales({ csvText, fileName, calendar, store, today = null }) {
  const parsed = parseSales(csvText);
  if (parsed.rows.length === 0) {
    throw new Error("읽을 수 있는 매출 기록이 없습니다. 파일 형식을 확인해 주세요.");
  }

  // 학사일정은 매출 파일이 아니라 우리 캘린더에서 날짜로 붙인다
  const { rows, uncovered } = attachAcademicEvents(parsed.rows, calendar);
  const menus = parsed.menus;
  const { prices, maxRelError } = estimateMenuPrices(rows, menus);

  const asOf = today ?? rows[rows.length - 1].date;
  const history = rows.filter((r) => r.date <= asOf);
  const weeks = groupFullWeeks(history);

  // 완전한 주가 3개는 있어야 "지난주 / 그 전 주 / 검증할 주"가 나온다
  if (weeks.length < 3) {
    return {
      ok: false,
      reason: `완전한 주가 ${weeks.length}주뿐입니다. 주간 분석과 예측에는 3주 이상이 필요합니다.`,
      upload: buildUploadResult({
        rows,
        prices,
        maxRelError,
        menus,
        weeksCovered: weeks.length,
        today: asOf,
        skipped: parsed.skipped,
        shape: parsed.shape,
        hasTime: parsed.hasTime,
        hasMenu: parsed.hasMenu,
        store,
        fileName,
      }),
    };
  }

  const analysisWeek = weeks[weeks.length - 1];
  const prevWeek = weeks[weeks.length - 2];
  const priorWeek = weeks[weeks.length - 3];

  const model = trainModel(history);
  const momentum = momentumFactor(model, history);

  // 예측 대상 주는 아직 매출 기록이 없다. 날짜와 학사일정만으로 7일을 만든다.
  const targetDays = buildFutureDays(calendar, addDays(analysisWeek.weekStart, 7), 7);

  // 결제 시각과 메뉴가 함께 있을 때만 판단할 수 있다.
  // 기준 시점 이후는 아직 모르는 데이터다 — 탐지에도 쓰지 않는다.
  const earlySalesEnds =
    parsed.hasTime && parsed.hasMenu
      ? detectEarlySalesEnds(
          { ...parsed, lastSold: parsed.lastSold.filter((e) => e.date <= asOf) },
          prices,
          store.id
        )
      : [];

  return {
    ok: true,
    meta: {
      fileName,
      asOf,
      estimatedPrices: prices,
      priceEstimationMaxError: maxRelError,
      weeksAvailable: weeks.length,
      shape: parsed.shape,
      uncoveredDays: uncovered,
    },
    store: { ...store, openedAt: rows[0].date, origin: "computed" },
    weeklyAnalysis: buildWeeklyAnalysis(
      analysisWeek,
      prevWeek,
      prices,
      menus,
      parsed.hourlyByDate,
      store.id
    ),
    forecast: buildForecast(
      model,
      analysisWeek,
      targetDays,
      momentum,
      weeks,
      history,
      calendar,
      store.id
    ),
    verification: buildVerification(history, weeks, prevWeek, priorWeek, store.id),
    upload: buildUploadResult({
      rows,
      prices,
      maxRelError,
      menus,
      weeksCovered: groupFullWeeks(rows).length,
      today: asOf,
      skipped: parsed.skipped,
      shape: parsed.shape,
      hasTime: parsed.hasTime,
      hasMenu: parsed.hasMenu,
      store,
      fileName,
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
}
