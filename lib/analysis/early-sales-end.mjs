/**
 * 평소보다 일찍 끊긴 메뉴를 찾는다.
 *
 * 결제 시각과 메뉴가 함께 있는 파일에서만 가능하다.
 * 확정하지 않는 것이 핵심이다 — 품절인지, 안 팔린 것인지, 그날 일찍 닫은 것인지는 사장님만 안다.
 */

import { fromMinutes, withJosa } from "./csv-read.mjs";

/** 정렬된 배열의 분위수 (선형 보간) */
function quantile(sorted, p) {
  if (sorted.length === 0) return 0;
  const idx = (sorted.length - 1) * p;
  const lo = Math.floor(idx);
  const hi = Math.ceil(idx);
  return lo === hi ? sorted[lo] : sorted[lo] + (sorted[hi] - sorted[lo]) * (idx - lo);
}

/** 그날 매장 전체가 언제까지 팔았는지 */
function storeCloseByDate(lastSold) {
  const byDate = new Map();
  for (const entry of lastSold) {
    const current = byDate.get(entry.date) ?? 0;
    if (entry.minutes > current) byDate.set(entry.date, entry.minutes);
  }
  return byDate;
}

/** 이 날짜의 n주 전 같은 요일 */
function weeksBefore(date, n) {
  const d = new Date(`${date}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() - 7 * n);
  return d.toISOString().slice(0, 10);
}

/**
 * 같은 요일에 몇 주 "연속으로" 같은 일이 있었는지 센다.
 * 1년에 흩어진 11번이 아니라, 바로 직전 주부터 이어진 횟수여야 의미가 있다.
 */
function countConsecutiveWeeks(date, flaggedDates) {
  let count = 1;
  while (flaggedDates.has(weeksBefore(date, count))) count += 1;
  return count;
}

/**
 * 평소보다 일찍 끊긴 메뉴를 찾는다.
 *
 * 확정하지 않는다. 품절일 수도, 안 팔린 것일 수도, 그날 일찍 닫은 것일 수도 있다.
 *
 * 함정이 둘 있어서 걸러낸다.
 *  1. 매장 전체가 일찍 닫은 날 — 메뉴 문제가 아니다.
 *  2. 그 메뉴가 적게 팔린 날 — 적게 팔리면 마지막 판매가 이른 게 당연하다. 사건이 아니라 산수다.
 *     그래서 판매량이 비슷한 날끼리만 비교한다.
 */
export function detectEarlySalesEnds(aggregate, prices, storeId, options = {}) {
  const { minGapMinutes = 60, minDays = 20, minComparable = 8, minQuantity = 3, limit = 5 } = options;
  const closeByDate = storeCloseByDate(aggregate.lastSold);
  const byMenu = new Map();

  for (const entry of aggregate.lastSold) {
    if (!byMenu.has(entry.menu)) byMenu.set(entry.menu, []);
    byMenu.get(entry.menu).push(entry);
  }

  const candidates = [];

  for (const [menu, entries] of byMenu) {
    if (entries.length < minDays) continue;

    for (const entry of entries) {
      // 두어 개 팔린 날은 일찍 끝났다는 말 자체가 성립하지 않는다
      if (entry.quantity < minQuantity) continue;

      // 판매량이 ±30% 안에 드는 날들만 비교 대상으로 삼는다
      const comparable = entries.filter(
        (e) => e.quantity >= entry.quantity * 0.7 && e.quantity <= entry.quantity * 1.3
      );
      if (comparable.length < minComparable) continue;

      const sorted = comparable.map((e) => e.minutes).sort((a, b) => a - b);
      // 평소 마감은 중앙값이 아니라 상위 분위로 본다 — "이만큼 팔리는 날이면 여기까지는 팔린다"
      const usual = Math.round(quantile(sorted, 0.7));
      const gap = usual - entry.minutes;
      if (gap < minGapMinutes) continue;

      // 매장 자체가 일찍 닫은 날이면 메뉴 문제가 아니다
      const storeClose = closeByDate.get(entry.date) ?? entry.minutes;
      if (storeClose - entry.minutes < 30) continue;

      candidates.push({ menu, entry, usual, gap, storeClose, comparable });
    }
  }

  // 메뉴별로 어느 날이 걸렸는지 기억해 두고 연속 반복을 센다
  const flaggedByMenu = new Map();
  for (const c of candidates) {
    if (!flaggedByMenu.has(c.menu)) flaggedByMenu.set(c.menu, new Set());
    flaggedByMenu.get(c.menu).add(c.entry.date);
  }
  for (const c of candidates) {
    c.repeatedWeeks = countConsecutiveWeeks(c.entry.date, flaggedByMenu.get(c.menu));
  }

  // 반복되는 패턴이 일회성 outlier보다 중요하다
  candidates.sort((a, b) => b.repeatedWeeks - a.repeatedWeeks || b.gap - a.gap);

  return candidates.slice(0, limit).map((c, i) => {
    const quantities = c.comparable.map((e) => e.quantity).sort((a, b) => a - b);
    const price = prices[c.menu] ?? 0;
    // 놓친 시간만큼 평소 판매량이 더 있었을 수 있다는 정도의 추정 — 실제 손실액이 아니다
    const openMinutes = Math.max(c.storeClose - 17 * 60, 1);
    const ratio = Math.min(c.gap / openMinutes, 1);
    const soldWell = c.entry.quantity >= quantile(quantities, 0.6);

    // 상·하한이 같으면 범위가 아니다. 최소한 한 개 차이는 두어 폭을 정직하게 남긴다.
    const low = Math.round((quantile(quantities, 0.25) * ratio * price) / 100) * 100;
    const high = Math.max(Math.round((quantile(quantities, 0.75) * ratio * price) / 100) * 100, low + price);

    return {
      id: `ese_${storeId}_${c.entry.date}_${i}`,
      storeId,
      date: c.entry.date,
      menuName: c.menu,
      lastSoldAt: fromMinutes(c.entry.minutes),
      usualClosingAt: fromMinutes(c.usual),
      earlierByMinutes: c.gap,
      opportunityRange: { low, high },
      repeatedWeeks: c.repeatedWeeks,
      possibleCauses: soldWell
        ? ["sold_out", "stopped_selling", "pos_missing"]
        : ["no_demand", "stopped_selling", "pos_missing"],
      reasoning: `${withJosa(c.menu, "이/가")} ${c.entry.quantity}개 팔린 날은 보통 ${fromMinutes(
        c.usual
      )}까지 이어졌는데(비슷한 날 ${c.comparable.length}일 기준) 이날은 ${fromMinutes(
        c.entry.minutes
      )}가 마지막이었습니다. 매장은 ${fromMinutes(c.storeClose)}까지 다른 메뉴를 팔고 있었습니다.`,
      confidence: c.repeatedWeeks >= 3 ? "high" : c.repeatedWeeks >= 2 ? "medium" : "low",
      ownerConfirmation: "unconfirmed",
      ownerNote: null,
      origin: "computed",
    };
  });
}
