/**
 * 결제 내역형 CSV(한 줄 = 결제 한 건)를 일별 집계로 접고,
 * 시각이 있어야만 알 수 있는 것들을 함께 뽑아낸다.
 *
 * 실제 POS는 대부분 이 형태다. 일별 집계 파일에는 없는 두 가지가 여기서 나온다.
 *  - 시간대별 매출
 *  - 어떤 메뉴가 언제까지 팔렸는지 (조기 종료 탐지는 early-sales-end.mjs)
 */

import {
  MENU_KEYS,
  QUANTITY_KEYS,
  REVENUE_KEYS,
  TIME_KEYS,
  findColumn,
  toClock,
  toISODate,
  toMinutes,
  toNumber,
} from "./csv-read.mjs";

/** 영업일 기준 분 — 새벽 6시 이전은 전날 영업의 연장으로 본다 (주점은 자정을 넘긴다) */
function businessMinutes(clock) {
  const m = toMinutes(clock);
  return m < 360 ? m + 1440 : m;
}

/**
 * 결제 내역을 하루 단위로 접는다.
 * 시각·메뉴·수량은 있으면 쓰고 없으면 그만큼 기능이 줄어든다 — 없는 걸 지어내지 않는다.
 */
export function aggregateTransactions(headers, records, dateKey) {
  const revenueKey = findColumn(headers, REVENUE_KEYS);
  const timeKey = findColumn(headers, TIME_KEYS);
  const menuKey = findColumn(headers, MENU_KEYS);
  const quantityKey = findColumn(headers, QUANTITY_KEYS);

  const days = new Map();
  const menus = new Set();
  const hourly = new Map();
  /** 메뉴별·날짜별 마지막 판매 시각(영업일 기준 분) */
  const lastSold = new Map();
  const skipped = { badDate: 0, missingRevenue: 0 };

  for (const record of records) {
    const date = toISODate(record[dateKey]);
    const amount = toNumber(record[revenueKey]);
    if (!date) {
      skipped.badDate += 1;
      continue;
    }
    if (amount === null) {
      skipped.missingRevenue += 1;
      continue;
    }

    // 시각 컬럼이 따로 없으면 날짜 컬럼 안에 붙어 있는지 본다
    const clock = timeKey ? toClock(record[timeKey]) : toClock(record[dateKey]);
    const menu = menuKey ? String(record[menuKey] ?? "").trim() : null;
    const quantity = quantityKey ? (toNumber(record[quantityKey]) ?? 1) : 1;

    if (!days.has(date)) days.set(date, { revenue: 0, orderCount: 0, quantities: {} });
    const day = days.get(date);
    day.revenue += amount;
    day.orderCount += 1;

    if (menu) {
      menus.add(menu);
      day.quantities[menu] = (day.quantities[menu] ?? 0) + quantity;
      if (clock) {
        const key = `${menu}|${date}`;
        const minutes = businessMinutes(clock);
        if (!lastSold.has(key) || lastSold.get(key).minutes < minutes) {
          lastSold.set(key, { menu, date, minutes });
        }
      }
    }

    if (clock) {
      const hour = Number(clock.slice(0, 2));
      // 날짜별로도 쌓아 둔다 — 주간 리포트는 그 주의 시간대만 봐야 한다
      if (!hourly.has(date)) hourly.set(date, new Map());
      const ofDay = hourly.get(date);
      if (!ofDay.has(hour)) ofDay.set(hour, { hour, revenue: 0, orderCount: 0 });
      const bucket = ofDay.get(hour);
      bucket.revenue += amount;
      bucket.orderCount += 1;
    }
  }

  const menuList = Array.from(menus).sort();
  const rows = Array.from(days.entries())
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([date, day]) => {
      const quantities = {};
      for (const menu of menuList) quantities[menu] = day.quantities[menu] ?? 0;
      return {
        date,
        weekday: new Date(`${date}T00:00:00Z`).getUTCDay(),
        quantities,
        totalQuantity: menuList.reduce((s, m) => s + quantities[m], 0),
        orderCount: day.orderCount,
        revenue: day.revenue,
      };
    });

  // 마지막 판매 시각에 "그날 그 메뉴가 몇 개 팔렸는지"를 붙인다.
  // 마지막 결제 한 건의 수량이 아니라 하루 총량이어야 판매량이 비슷한 날끼리 비교할 수 있다.
  const quantityByKey = new Map();
  for (const row of rows) {
    for (const menu of menuList) quantityByKey.set(`${menu}|${row.date}`, row.quantities[menu]);
  }
  const lastSoldWithVolume = Array.from(lastSold.entries()).map(([key, entry]) => ({
    ...entry,
    quantity: quantityByKey.get(key) ?? 0,
  }));

  return {
    rows,
    menus: menuList,
    hourlyByDate: hourly,
    lastSold: lastSoldWithVolume,
    hasTime: hourly.size > 0,
    hasMenu: menuList.length > 0,
    skipped,
  };
}

/** 지정한 날짜들의 시간대별 매출을 합친다 */
export function hourlyForDates(hourlyByDate, dates) {
  if (!hourlyByDate) return [];
  const merged = new Map();
  for (const date of dates) {
    for (const bucket of (hourlyByDate.get(date) ?? new Map()).values()) {
      if (!merged.has(bucket.hour)) merged.set(bucket.hour, { hour: bucket.hour, revenue: 0, orderCount: 0 });
      const target = merged.get(bucket.hour);
      target.revenue += bucket.revenue;
      target.orderCount += bucket.orderCount;
    }
  }
  return Array.from(merged.values()).sort((a, b) => a.hour - b.hour);
}
