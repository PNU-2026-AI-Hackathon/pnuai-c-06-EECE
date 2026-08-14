/**
 * CSV를 읽는 저수준 도구 모음.
 *
 * POS마다 컬럼 이름이 다르고, 파일 모양도 두 가지다.
 *  - daily:       하루 한 줄로 이미 집계된 파일
 *  - transaction: 결제 한 건이 한 줄인 파일 (실제 POS는 대개 이쪽)
 * 어느 쪽인지 판단하는 것까지가 이 파일의 몫이다.
 */

import fs from "node:fs";

/** 날짜로 볼 수 있는 컬럼 이름 후보 */
export const DATE_KEYS = ["date", "날짜", "영업일", "거래일", "판매일", "일자", "결제일", "결제일시", "거래일시"];
/** 매출 금액 컬럼 후보 */
export const REVENUE_KEYS = ["총매출", "매출", "매출금액", "결제금액", "판매금액", "금액", "amount", "total"];
/** 결제 시각 컬럼 후보 */
export const TIME_KEYS = ["time", "시간", "시각", "거래시간", "결제시간", "결제시각", "판매시간"];
/** 메뉴명 컬럼 후보 */
export const MENU_KEYS = ["menu", "메뉴", "메뉴명", "상품명", "품목", "품목명"];
/** 수량 컬럼 후보 */
export const QUANTITY_KEYS = ["quantity", "수량", "판매수량", "개수"];

/** 따옴표를 고려해 한 줄을 셀로 나눈다 */
export function splitLine(line) {
  const cells = [];
  let current = "";
  let quoted = false;
  for (const char of line) {
    if (char === '"') quoted = !quoted;
    else if (char === "," && !quoted) {
      cells.push(current.trim());
      current = "";
    } else current += char;
  }
  cells.push(current.trim());
  return cells;
}

/** 후보와 일치하는 첫 컬럼 찾기 (공백·대소문자 무시) */
export function findColumn(headers, candidates) {
  const normalized = headers.map((h) => h.replace(/\s/g, "").toLowerCase());
  for (const candidate of candidates) {
    const idx = normalized.indexOf(candidate.toLowerCase());
    if (idx !== -1) return headers[idx];
  }
  return null;
}

/** "소주_판매수량"처럼 메뉴가 컬럼으로 펼쳐진 형태를 찾는다 */
export function findMenuColumns(headers) {
  return headers
    .filter((h) => /_판매수량$|_수량$/.test(h))
    .map((h) => ({ column: h, menu: h.replace(/_판매수량$|_수량$/, "") }));
}

/** "1,234원" → 1234 */
export function toNumber(value) {
  if (value === undefined || value === null) return null;
  const cleaned = String(value).replace(/[^\d.-]/g, "");
  if (cleaned === "") return null;
  const n = Number(cleaned);
  return Number.isFinite(n) ? n : null;
}

/** YYYY-MM-DD / YYYY.MM.DD / YYYY/MM/DD → ISO 날짜 */
export function toISODate(value) {
  const m = String(value ?? "").match(/(\d{4})[-./](\d{1,2})[-./](\d{1,2})/);
  if (!m) return null;
  const [, y, mo, d] = m;
  if (+mo < 1 || +mo > 12 || +d < 1 || +d > 31) return null;
  return `${y}-${String(+mo).padStart(2, "0")}-${String(+d).padStart(2, "0")}`;
}

/**
 * "19:23:00" / "2025-10-19 19:23" → "19:23".
 * 날짜 컬럼 하나에 시각까지 들어 있는 파일이 많아 같은 값에서 두 번 꺼낼 수 있게 한다.
 */
export function toClock(value) {
  const m = String(value ?? "").match(/(?:^|\s|T)(\d{1,2}):(\d{2})/);
  if (!m) return null;
  const [, h, min] = m;
  if (+h > 23 || +min > 59) return null;
  return `${String(+h).padStart(2, "0")}:${min}`;
}

/** "19:23" → 1163 (분) */
export function toMinutes(clock) {
  const [h, m] = clock.split(":").map(Number);
  return h * 60 + m;
}

/** 1163 → "19:23" */
export function fromMinutes(minutes) {
  const wrapped = ((minutes % 1440) + 1440) % 1440;
  return `${String(Math.floor(wrapped / 60)).padStart(2, "0")}:${String(wrapped % 60).padStart(2, "0")}`;
}

/**
 * 받침 유무에 맞는 조사를 붙인다. "김치전가"가 아니라 "김치전이"여야 한다.
 * 메뉴명은 매장마다 다르므로 문장을 만들 때마다 판단해야 한다.
 */
export function withJosa(word, pair) {
  const [withFinal, withoutFinal] = pair.split("/");
  const last = word.charCodeAt(word.length - 1);
  // 한글 음절이 아니면 (숫자·영문 등) 받침 없는 쪽으로 둔다
  if (last < 0xac00 || last > 0xd7a3) return `${word}${withoutFinal}`;
  return `${word}${(last - 0xac00) % 28 > 0 ? withFinal : withoutFinal}`;
}

/** 파일을 읽어 헤더와 레코드 배열로 */
export function readTable(filePath) {
  const text = fs.readFileSync(filePath, "utf8").replace(/^﻿/, "").trim();
  const [headerLine, ...lines] = text.split(/\r?\n/);
  const headers = splitLine(headerLine);
  const records = lines
    .filter((line) => line.trim() !== "")
    .map((line) => {
      const cells = splitLine(line);
      return Object.fromEntries(headers.map((h, i) => [h, cells[i]]));
    });
  return { headers, records };
}

/**
 * 파일 모양을 판단한다.
 *
 * 메뉴가 컬럼으로 펼쳐져 있으면 일별 집계다.
 * 메뉴명 컬럼이 따로 있거나 같은 날짜가 여러 줄이면 결제 내역이다.
 */
export function detectShape(headers, records, dateKey) {
  if (findMenuColumns(headers).length > 0) return "daily";
  if (findColumn(headers, MENU_KEYS)) return "transaction";
  if (findColumn(headers, TIME_KEYS)) return "transaction";

  const dates = records.map((r) => toISODate(r[dateKey])).filter(Boolean);
  const unique = new Set(dates).size;
  return unique > 0 && dates.length > unique * 1.5 ? "transaction" : "daily";
}
