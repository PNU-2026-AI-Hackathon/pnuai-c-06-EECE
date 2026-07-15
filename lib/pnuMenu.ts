// lib/pnuMenu.ts — 부산대 식단 파싱 (프론트 pnu_menu_service.dart 검증 로직 이식)
import * as cheerio from 'cheerio';

export interface MenuSection {
  name: string; // 정식 | 일품 | 특정식
  price: number; // 5000 등
  items: string[]; // 메뉴 품목들
}

export interface DayMenu {
  date: string; // 'YYYY-MM-DD'
  lunch: MenuSection[];
  dinner: MenuSection[];
}

const DATE_RE = /(\d{4})\.(\d{2})\.(\d{2})/;
const SECTION_RE = /^(정식|일품|특정식)\s*-\s*([\d,]+)\s*원/;

/** 셀 innerHTML → 섹션들 ("정식-5,000원<br>흑미밥<br>육개장..." 구조) */
function parseSections(cellHtml: string): MenuSection[] {
  const lines = cellHtml
    .split(/<br\s*\/?>/i)
    .map((s) => s.replace(/<[^>]+>/g, '').trim())
    .filter(Boolean);
  const sections: MenuSection[] = [];
  let name: string | null = null;
  let price = 0;
  let items: string[] = [];
  const flush = () => {
    if (name && items.length) sections.push({ name, price, items });
    items = [];
  };
  for (const line of lines) {
    const m = line.match(SECTION_RE);
    if (m) {
      flush();
      name = m[1];
      price = parseInt(m[2].replace(/,/g, ''), 10);
    } else if (name) {
      items.push(line);
    }
  }
  flush();
  return sections;
}

/** 주간 테이블 파싱. staff=true면 중식만 수집 (교직원 페이지) */
export function parseBuildingWeek(html: string, staff: boolean): DayMenu[] {
  const $ = cheerio.load(html);
  let dates: Map<number, string> | null = null; // 셀 인덱스 → 'YYYY-MM-DD'
  const byDate = new Map<string, DayMenu>();

  $('tr').each((_, tr) => {
    const cells = $(tr).find('th,td').toArray();
    if (!cells.length) return;

    // 1) 헤더 행(날짜들) 탐지 — 날짜가 2개 이상인 첫 행
    if (!dates) {
      const found = new Map<number, string>();
      cells.forEach((c, i) => {
        const m = $(c).text().match(DATE_RE);
        if (m) found.set(i, `${m[1]}-${m[2]}-${m[3]}`);
      });
      if (found.size >= 2) dates = found;
      return;
    }

    // 2) 식사 행 (중식/석식)
    const dateMap = dates;
    const label = $(cells[0]).text();
    const isLunch = label.includes('중식');
    const isDinner = label.includes('석식');
    if (!isLunch && !isDinner) return;
    if (staff && !isLunch) return;

    for (const [idx, date] of dateMap) {
      if (idx >= cells.length) continue;
      const sections = parseSections($(cells[idx]).html() ?? '');
      if (!sections.length) continue;
      const day = byDate.get(date) ?? { date, lunch: [], dinner: [] };
      if (isLunch) day.lunch = sections;
      else day.dinner = sections;
      byDate.set(date, day);
    }
  });

  return [...byDate.values()].sort((a, b) => a.date.localeCompare(b.date));
}
