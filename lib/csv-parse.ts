import type { AnalysisCapability, MenuNormalization, UploadResult, UploadWarning } from "@/types";

/**
 * 브라우저에서 POS CSV를 읽어 업로드 결과를 만든다.
 * 백엔드가 생기면 이 로직은 서버로 옮겨가고, 화면은 같은 UploadResult를 받는다.
 * 컬럼 이름은 POS마다 다르므로 후보를 여러 개 두고 찾는다.
 */

/** 날짜로 볼 수 있는 컬럼 이름 후보 */
const DATE_KEYS = ["date", "날짜", "영업일", "거래일", "판매일", "일자"];
/** 매출 금액 컬럼 후보 */
const REVENUE_KEYS = ["총매출", "매출", "매출금액", "결제금액", "판매금액", "금액", "amount", "total"];
/** 결제 시각 컬럼 후보 */
const TIME_KEYS = ["time", "시간", "거래시간", "결제시간"];
/** 메뉴명 컬럼 후보 */
const MENU_KEYS = ["menu", "메뉴", "메뉴명", "상품명", "품목"];
/** 수량 컬럼 후보 */
const QUANTITY_KEYS = ["quantity", "수량", "판매수량", "개수"];

/** 헤더 목록에서 후보와 일치하는 첫 컬럼 찾기 */
function findColumn(headers: string[], candidates: string[]): string | null {
  const normalized = headers.map((h) => h.replace(/\s/g, "").toLowerCase());
  for (const candidate of candidates) {
    const idx = normalized.indexOf(candidate.toLowerCase());
    if (idx !== -1) return headers[idx];
  }
  return null;
}

/** "소주_판매수량" 처럼 메뉴명이 컬럼으로 펼쳐진 형태인지 */
function findMenuColumns(headers: string[]): { column: string; menu: string }[] {
  return headers
    .filter((h) => /_판매수량$|_수량$/.test(h))
    .map((h) => ({ column: h, menu: h.replace(/_판매수량$|_수량$/, "") }));
}

/** 따옴표를 고려한 한 줄 분해 */
function splitLine(line: string): string[] {
  const cells: string[] = [];
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

/** "1,234원" → 1234 */
function toNumber(value: string | undefined): number | null {
  if (!value) return null;
  const cleaned = value.replace(/[^\d.-]/g, "");
  if (cleaned === "") return null;
  const n = Number(cleaned);
  return Number.isFinite(n) ? n : null;
}

/** YYYY-MM-DD / YYYY.MM.DD / YYYY/MM/DD 를 ISO 날짜로 */
function toISODate(value: string | undefined): string | null {
  if (!value) return null;
  const m = value.match(/(\d{4})[-./](\d{1,2})[-./](\d{1,2})/);
  if (!m) return null;
  const [, y, mo, d] = m;
  const month = Number(mo);
  const day = Number(d);
  if (month < 1 || month > 12 || day < 1 || day > 31) return null;
  return `${y}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

/** 완전한 주(월~일)가 몇 개인지 */
function countFullWeeks(dates: string[]): number {
  const days = new Set(dates);
  const weeks = new Map<string, number>();
  for (const date of Array.from(days)) {
    const d = new Date(`${date}T00:00:00Z`);
    d.setUTCDate(d.getUTCDate() - ((d.getUTCDay() + 6) % 7));
    const key = d.toISOString().slice(0, 10);
    weeks.set(key, (weeks.get(key) ?? 0) + 1);
  }
  return Array.from(weeks.values()).filter((n) => n >= 6).length;
}

/** 이 파일로 가능한 분석 목록 */
function buildCapabilities(has: {
  time: boolean;
  menu: boolean;
  weeks: number;
}): AnalysisCapability[] {
  return [
    { kind: "daily_sales", label: "일별 매출", available: true, missingReason: null },
    {
      kind: "weekday_pattern",
      label: "요일별 패턴",
      available: has.weeks >= 2,
      missingReason: has.weeks >= 2 ? null : "완전한 주가 2주 이상 있어야 요일 패턴을 볼 수 있습니다.",
    },
    {
      kind: "menu_analysis",
      label: "메뉴별 분석",
      available: has.menu,
      missingReason: has.menu ? null : "메뉴 정보가 없어 메뉴별 분석은 할 수 없습니다.",
    },
    {
      kind: "hourly_pattern",
      label: "시간대별 매출",
      available: has.time,
      missingReason: has.time ? null : "결제 시각이 없어 시간대별 매출은 만들 수 없습니다.",
    },
    {
      kind: "academic_event",
      label: "학사일정 비교",
      available: has.weeks >= 8,
      missingReason:
        has.weeks >= 8 ? null : `학사일정과 비교하려면 8주 이상이 필요합니다. 지금은 ${has.weeks}주입니다.`,
    },
    {
      kind: "early_sales_end",
      label: "판매 조기 종료 탐지",
      available: has.time && has.menu,
      missingReason:
        has.time && has.menu ? null : "결제 시각과 메뉴가 함께 있어야 판매가 일찍 끝났는지 알 수 있습니다.",
    },
  ];
}

/** 파싱 실패 시 던지는 오류 — 메시지는 사장님에게 그대로 보여준다 */
export class CsvParseError extends Error {}

/**
 * CSV 텍스트 → UploadResult.
 * 못 읽는 파일은 추측하지 않고 무엇이 없는지 알려준다.
 */
export function parseSalesCsv(text: string, fileName: string, storeId: string): UploadResult {
  const clean = text.replace(/^﻿/, "").trim();
  const lines = clean.split(/\r?\n/).filter((l) => l.trim() !== "");
  if (lines.length < 2) throw new CsvParseError("파일에 데이터가 없습니다. 다른 파일을 올려주세요.");

  const headers = splitLine(lines[0]);
  const dateKey = findColumn(headers, DATE_KEYS);
  const revenueKey = findColumn(headers, REVENUE_KEYS);
  const timeKey = findColumn(headers, TIME_KEYS);
  const menuKey = findColumn(headers, MENU_KEYS);
  const quantityKey = findColumn(headers, QUANTITY_KEYS);
  const menuColumns = findMenuColumns(headers);

  if (!dateKey) throw new CsvParseError("날짜 컬럼을 찾지 못했습니다. 날짜가 들어간 파일인지 확인해 주세요.");
  if (!revenueKey) throw new CsvParseError("매출 금액 컬럼을 찾지 못했습니다. 금액이 들어간 파일이어야 합니다.");

  const dates: string[] = [];
  const menuTotals = new Map<string, number>();
  let processedRows = 0;
  let missingValueRows = 0;
  let badDateRows = 0;
  const seen = new Set<string>();
  let duplicateRows = 0;

  for (const line of lines.slice(1)) {
    const cells = splitLine(line);
    const row = Object.fromEntries(headers.map((h, i) => [h, cells[i]]));
    const date = toISODate(row[dateKey]);
    const revenue = toNumber(row[revenueKey]);

    if (!date) {
      badDateRows += 1;
      continue;
    }
    if (revenue === null) {
      missingValueRows += 1;
      continue;
    }

    const signature = `${date}|${row[timeKey ?? ""] ?? ""}|${row[menuKey ?? ""] ?? ""}|${revenue}`;
    if (seen.has(signature)) duplicateRows += 1;
    seen.add(signature);

    dates.push(date);
    processedRows += 1;

    for (const { column, menu } of menuColumns) {
      const qty = toNumber(row[column]) ?? 0;
      if (qty > 0) menuTotals.set(menu, (menuTotals.get(menu) ?? 0) + qty);
    }
    if (menuKey && row[menuKey]) {
      const qty = quantityKey ? (toNumber(row[quantityKey]) ?? 1) : 1;
      menuTotals.set(row[menuKey], (menuTotals.get(row[menuKey]) ?? 0) + qty);
    }
  }

  if (processedRows === 0) {
    throw new CsvParseError("읽을 수 있는 매출 기록이 없습니다. 파일 형식을 확인해 주세요.");
  }

  const sorted = [...dates].sort();
  const weeksCovered = countFullWeeks(dates);
  const hasMenu = menuColumns.length > 0 || Boolean(menuKey);

  const menuNormalizations: MenuNormalization[] = Array.from(menuTotals.entries())
    .sort((a, b) => b[1] - a[1])
    .map(([raw, count]) => ({
      rawName: raw,
      normalizedName: raw.replace(/\(.*\)|\s/g, ""),
      confidence: /[A-Za-z]/.test(raw) || raw.length <= 2 ? 0.7 : 1,
      occurrences: count,
    }));

  const warnings: UploadWarning[] = [];
  if (badDateRows > 0) {
    warnings.push({
      code: "UNPARSABLE_DATE",
      level: "error",
      message: `날짜를 읽을 수 없는 행 ${badDateRows}건을 제외했습니다.`,
      affectedRows: badDateRows,
    });
  }
  if (missingValueRows > 0) {
    warnings.push({
      code: "MISSING_VALUE",
      level: "warning",
      message: `금액이 비어 있는 행 ${missingValueRows}건을 제외했습니다.`,
      affectedRows: missingValueRows,
    });
  }
  if (duplicateRows > 0) {
    warnings.push({
      code: "DUPLICATE_ROW",
      level: "warning",
      message: `완전히 같은 기록 ${duplicateRows}건이 중복으로 보입니다. 한 건씩만 셌습니다.`,
      affectedRows: duplicateRows,
    });
  }
  if (!timeKey) {
    warnings.push({
      code: "MISSING_VALUE",
      level: "warning",
      message: "결제 시각이 없는 일별 집계 파일입니다. 시간대별 분석은 제외했습니다.",
      affectedRows: 0,
    });
  }

  return {
    id: `upload_${Date.now()}`,
    storeId,
    fileName,
    uploadedAt: new Date().toISOString().slice(0, 19),
    processedRows,
    skippedRows: badDateRows + missingValueRows,
    period: { start: sorted[0], end: sorted[sorted.length - 1] },
    recognizedMenuCount: menuTotals.size,
    menuNormalizations,
    warnings,
    capabilities: buildCapabilities({ time: Boolean(timeKey), menu: hasMenu, weeks: weeksCovered }),
    weeksCovered,
  };
}
