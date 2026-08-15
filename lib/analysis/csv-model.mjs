/**
 * 술집 POS 일별 집계 CSV를 읽어 예측 모델을 만드는 순수 함수 모음.
 * 백엔드(FastAPI)가 생기면 이 로직이 서버로 옮겨간다. 여기서는 목 데이터 생성에만 쓴다.
 */

import {
  DATE_KEYS,
  REVENUE_KEYS,
  detectShape,
  findColumn,
  findMenuColumns,
  parseTable,
  toISODate,
  toNumber,
} from "./csv-read.mjs";
import { aggregateTransactions } from "./transaction-csv.mjs";

/** 일별 집계 파일 — 하루가 이미 한 줄로 접혀 있다 */
function parseDailyTable(headers, records, dateKey, revenueKey) {
  const menuColumns = findMenuColumns(headers);
  const menus = menuColumns.map((m) => m.menu);
  const rows = [];
  const skipped = { badDate: 0, missingRevenue: 0 };

  for (const raw of records) {
    const date = toISODate(raw[dateKey]);
    const revenue = toNumber(raw[revenueKey]);
    if (!date) {
      skipped.badDate += 1;
      continue;
    }
    if (revenue === null) {
      skipped.missingRevenue += 1;
      continue;
    }

    const quantities = {};
    for (const { column, menu } of menuColumns) quantities[menu] = toNumber(raw[column]) ?? 0;

    rows.push({
      date,
      weekday: new Date(`${date}T00:00:00Z`).getUTCDay(),
      quantities,
      totalQuantity: menus.reduce((s, m) => s + quantities[m], 0),
      orderCount: null,
      revenue,
    });
  }

  return {
    rows,
    menus,
    skipped,
    hourlyByDate: null,
    lastSold: [],
    hasTime: false,
    hasMenu: menus.length > 0,
  };
}

/**
 * 매출 CSV를 읽는다. 일별 집계든 결제 내역이든 같은 모양으로 돌려준다.
 *
 * 필수는 날짜와 금액 둘뿐이다. 요일·주 시작일·총수량은 날짜와 수량에서 계산한다.
 * 학사일정은 여기서 읽지 않는다 — 실제 POS 파일에 없는 정보이기 때문이다.
 */
export function parseSales(csvText) {
  const { headers, records } = parseTable(csvText);

  const dateKey = findColumn(headers, DATE_KEYS);
  const revenueKey = findColumn(headers, REVENUE_KEYS);
  if (!dateKey) throw new Error("날짜 컬럼을 찾지 못했습니다. 확인한 후보: " + DATE_KEYS.join(", "));
  if (!revenueKey) throw new Error("매출 금액 컬럼을 찾지 못했습니다. 확인한 후보: " + REVENUE_KEYS.join(", "));

  const shape = detectShape(headers, records, dateKey);
  const parsed =
    shape === "transaction"
      ? aggregateTransactions(headers, records, dateKey)
      : parseDailyTable(headers, records, dateKey, revenueKey);

  parsed.rows.sort((a, b) => a.date.localeCompare(b.date));
  for (const row of parsed.rows) row.weekStart = weekStartOf(row.date);

  return { ...parsed, shape, rawRows: records.length, columns: { date: dateKey, revenue: revenueKey } };
}

/** 정규방정식 + 가우스 소거로 최소제곱해를 구한다 (메뉴 단가 역산용) */
function solveLeastSquares(A, b) {
  const n = A[0].length;
  const M = Array.from({ length: n }, (_, i) =>
    Array.from({ length: n + 1 }, (_, j) =>
      j === n
        ? A.reduce((s, row, r) => s + row[i] * b[r], 0)
        : A.reduce((s, row) => s + row[i] * row[j], 0)
    )
  );

  for (let c = 0; c < n; c++) {
    let pivot = c;
    for (let r = c + 1; r < n; r++) if (Math.abs(M[r][c]) > Math.abs(M[pivot][c])) pivot = r;
    [M[c], M[pivot]] = [M[pivot], M[c]];
    const d = M[c][c];
    for (let j = c; j <= n; j++) M[c][j] /= d;
    for (let r = 0; r < n; r++) {
      if (r === c) continue;
      const f = M[r][c];
      for (let j = c; j <= n; j++) M[r][j] -= f * M[c][j];
    }
  }
  return M.map((row) => row[n]);
}

/**
 * 메뉴별 단가를 매출·수량에서 역산한다.
 * CSV에 단가 컬럼이 없으므로 추정하되, 잔차를 함께 돌려줘 추정이 맞는지 확인할 수 있게 한다.
 */
export function estimateMenuPrices(rows, menus) {
  if (menus.length === 0) return { prices: {}, maxRelError: 0 };
  const A = rows.map((r) => menus.map((m) => r.quantities[m]));
  const b = rows.map((r) => r.revenue);
  const raw = solveLeastSquares(A, b);
  const prices = Object.fromEntries(menus.map((m, i) => [m, Math.round(raw[i] / 100) * 100]));

  const maxRelError = rows.reduce((worst, r) => {
    const predicted = menus.reduce((s, m) => s + prices[m] * r.quantities[m], 0);
    return Math.max(worst, Math.abs(predicted - r.revenue) / r.revenue);
  }, 0);

  return { prices, maxRelError };
}

/** 월요일 시작 주의 시작일 */
export function weekStartOf(date) {
  const d = new Date(`${date}T00:00:00Z`);
  const offset = (d.getUTCDay() + 6) % 7;
  d.setUTCDate(d.getUTCDate() - offset);
  return d.toISOString().slice(0, 10);
}

/** n일 뒤 날짜 */
export function addDays(date, n) {
  const d = new Date(`${date}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

/** 주 단위로 묶기 (7일이 모두 있는 주만) */
export function groupFullWeeks(rows) {
  const byWeek = new Map();
  for (const r of rows) {
    const key = weekStartOf(r.date);
    if (!byWeek.has(key)) byWeek.set(key, []);
    byWeek.get(key).push(r);
  }
  return [...byWeek.entries()]
    .filter(([, days]) => days.length === 7)
    .map(([weekStart, days]) => ({
      weekStart,
      weekEnd: addDays(weekStart, 6),
      days: days.sort((a, b) => a.date.localeCompare(b.date)),
      revenue: days.reduce((s, d) => s + d.revenue, 0),
    }))
    .sort((a, b) => a.weekStart.localeCompare(b.weekStart));
}

const mean = (xs) => xs.reduce((s, x) => s + x, 0) / (xs.length || 1);

/**
 * 학습: 기준 일매출 · 요일 계수 · 학사이벤트 계수.
 * 곱셈 모형이라 각 요인의 기여도를 로그로 분해해 근거로 보여줄 수 있다.
 */
export function trainModel(rows, baseLabel = "일반 학기") {
  const regular = rows.filter((r) => r.event === baseLabel);
  const base = mean(regular.map((r) => r.revenue));

  const weekdayFactor = {};
  for (let wd = 0; wd < 7; wd++) {
    const sample = regular.filter((r) => r.weekday === wd);
    weekdayFactor[wd] = sample.length ? mean(sample.map((r) => r.revenue)) / base : 1;
  }

  const eventFactor = {};
  const eventSampleDays = {};
  for (const event of new Set(rows.map((r) => r.event))) {
    const sample = rows.filter((r) => r.event === event);
    eventFactor[event] = mean(sample.map((r) => r.revenue / (base * weekdayFactor[r.weekday])));
    eventSampleDays[event] = sample.length;
  }

  return { base, weekdayFactor, eventFactor, eventSampleDays, trainedRows: rows.length };
}

/** 하루 매출 예측 (모멘텀 미적용) */
export function predictDay(model, weekday, event) {
  const ef = model.eventFactor[event] ?? 1;
  return model.base * model.weekdayFactor[weekday] * ef;
}

/** 최근 n주 실적이 모델 기준보다 얼마나 높/낮았는지 (추세 보정 계수) */
export function momentumFactor(model, rows, weeks = 3) {
  const recent = rows.slice(-7 * weeks);
  if (recent.length === 0) return 1;
  const predicted = recent.reduce((s, r) => s + predictDay(model, r.weekday, r.event), 0);
  const actual = recent.reduce((s, r) => s + r.revenue, 0);
  return predicted === 0 ? 1 : actual / predicted;
}

/** 정렬된 배열에서 분위수 (선형 보간) */
function quantile(sorted, p) {
  if (sorted.length === 0) return 1;
  const idx = (sorted.length - 1) * p;
  const lo = Math.floor(idx);
  const hi = Math.ceil(idx);
  return lo === hi ? sorted[lo] : sorted[lo] + (sorted[hi] - sorted[lo]) * (idx - lo);
}

/**
 * 주 단위 예측이 과거에 얼마나 빗나갔는지로 예측 범위를 만든다.
 * 실제/예측 비율의 20~80% 분위를 쓰고, 비교 사례가 적으면 범위를 넓힌다.
 * 좁은 범위로 확신하는 것보다 넓은 범위로 정직한 편이 낫다.
 *
 * 각 주의 예측에는 **그 주 시점의 모멘텀**을 쓴다.
 * 오늘의 모멘텀을 과거에 소급 적용하면 오차가 아니라 모멘텀 자체를 재게 되고,
 * 그러면 뒤에서 하는 보정이 모멘텀을 그대로 되돌려 버린다.
 */
export function forecastSpread(model, weeks, rows, eventDayCount) {
  const ratios = weeks
    .map((week) => {
      const before = rows.filter((r) => r.date < week.weekStart);
      // 앞선 데이터가 3주도 안 되면 그 주는 오차 표본으로 쓰지 않는다
      if (before.length < 21) return null;
      const pastMomentum = momentumFactor(model, before);
      const predicted =
        week.days.reduce((acc, d) => acc + predictDay(model, d.weekday, d.event), 0) * pastMomentum;
      return predicted > 0 ? week.revenue / predicted : null;
    })
    .filter((r) => r !== null)
    .sort((a, b) => a - b);

  const low = quantile(ratios, 0.2);
  const high = quantile(ratios, 0.8);
  // 모델이 한쪽으로 꾸준히 치우쳐 있으면 그 편향은 범위가 아니라 예측값에 반영해야 한다.
  // 그러지 않으면 "예측 19% (범위 25~42%)" 처럼 중앙값이 자기 범위 밖으로 나간다.
  const median = quantile(ratios, 0.5);

  // 같은 이벤트 표본이 10일 미만이면 그만큼 범위를 넓힌다
  const widen = eventDayCount >= 10 ? 1 : Math.sqrt(10 / Math.max(eventDayCount, 1));
  return {
    median,
    low: median - (median - low) * widen,
    high: median + (high - median) * widen,
    coverage: 60,
  };
}

/**
 * 과거에 같은 학사이벤트가 몇 번 있었는지 센다.
 * 연속된 날짜는 한 번으로 묶는다 (중간고사 5일 = 1회).
 */
export function countEventCases(rows, eventLabel) {
  let caseCount = 0;
  let dayCount = 0;
  let inRun = false;

  for (const row of rows) {
    if (row.event === eventLabel) {
      dayCount += 1;
      if (!inRun) caseCount += 1;
      inRun = true;
    } else {
      inRun = false;
    }
  }
  return { caseCount, dayCount };
}

/**
 * 곱셈 요인들의 기여도를 합이 정확히 총 증감률이 되도록 분해한다.
 * factors: [{ label, factor, source, detail }]
 */
export function decomposeContributions(factors, totalChangeRate) {
  const logs = factors.map((f) => Math.log(f.factor));
  const logSum = logs.reduce((s, l) => s + l, 0);
  if (logSum === 0) return factors.map((f) => ({ ...f, contribution: 0 }));

  const raw = logs.map((l) => (l / logSum) * totalChangeRate);
  const rounded = raw.map((v) => Math.round(v));
  const drift = Math.round(totalChangeRate) - rounded.reduce((s, v) => s + v, 0);

  // 반올림 오차는 기여도가 가장 큰 항목에 몰아넣어 합계를 정확히 맞춘다
  let biggest = 0;
  raw.forEach((v, i) => {
    if (Math.abs(v) > Math.abs(raw[biggest])) biggest = i;
  });
  rounded[biggest] += drift;

  return factors.map((f, i) => ({ ...f, contribution: rounded[i] }));
}
