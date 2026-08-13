/**
 * 술집 POS 일별 집계 CSV를 읽어 예측 모델을 만드는 순수 함수 모음.
 * 백엔드(FastAPI)가 생기면 이 로직이 서버로 옮겨간다. 여기서는 목 데이터 생성에만 쓴다.
 */

import fs from "node:fs";

/** CSV 컬럼명 → 표준 메뉴명 */
export const MENU_COLUMNS = {
  소주_판매수량: "소주",
  맥주_판매수량: "맥주",
  하이볼_판매수량: "하이볼",
  닭발_판매수량: "닭발",
  오돌뼈_판매수량: "오돌뼈",
  김치전_판매수량: "김치전",
  계란찜_판매수량: "계란찜",
};

/** CSV를 파싱해 일별 레코드 배열로 */
export function parseCsv(path) {
  const text = fs.readFileSync(path, "utf8").replace(/^﻿/, "").trim();
  const [headerLine, ...lines] = text.split("\n");
  const headers = headerLine.split(",").map((h) => h.trim());

  return lines.map((line) => {
    const cells = line.split(",");
    const row = Object.fromEntries(headers.map((h, i) => [h, cells[i]?.trim()]));
    const quantities = {};
    for (const [col, menu] of Object.entries(MENU_COLUMNS)) quantities[menu] = Number(row[col] ?? 0);
    return {
      date: row.date,
      weekdayName: row.요일,
      weekday: new Date(`${row.date}T00:00:00Z`).getUTCDay(),
      event: row.학사이벤트,
      quantities,
      totalQuantity: Number(row.총판매수량),
      revenue: Number(row.총매출),
      weekStart: row.주_시작일,
    };
  });
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
export function estimateMenuPrices(rows) {
  const menus = Object.values(MENU_COLUMNS);
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
export function trainModel(rows) {
  const regular = rows.filter((r) => r.event === "일반 학기");
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
