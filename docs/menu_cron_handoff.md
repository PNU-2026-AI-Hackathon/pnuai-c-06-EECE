# 식단 크론 핸드오프 — 부산대 식단 파싱 TS 이식본

> 프론트(강현) → 백엔드(조우진). 2026-07-15.
> 원본: `lib/data/api/pnu_menu_service.dart` (실기기에서 검증 완료된 파싱 로직).
> 아래 TS는 그 로직을 그대로 이식한 것 — 파싱 함수는 복붙 가능, DB upsert만
> 조우진님 스키마에 맞춰 마무리하면 됨.

## 1. 수집 대상 (검증된 URL)

| 대상 | URL |
| :-- | :-- |
| 학생식당 (주간 중식/석식) | `https://www.pusan.ac.kr/kor/CMS/MenuMgr/menuListOnBuilding.do?mCode=MN202&campus_gb=PUSAN&building_gb=R001&restaurant_code=PG002` |
| 교직원식당 (주간 중식) | `https://www.pusan.ac.kr/kor/CMS/MenuMgr/menuListOnBuilding.do?mCode=MN202` (기본값) |

- 인코딩 UTF-8, 인증 불필요. 서버에서 fetch하면 CORS 무관.
- 확인된 가격: 학생 정식/일품 5,000원 · 교직원 정식 6,500원 (파싱으로 자동 추출됨)

## 2. HTML 구조 (파싱 규칙의 근거)

- 주간 테이블: **열 = 날짜(월~토), 행 = 조식/중식/석식**
- 헤더 행: 셀 텍스트에 `2026.07.13` 형식 날짜가 2개 이상 들어있는 첫 `<tr>`
  → 셀 인덱스별 날짜 매핑을 만든다 (rowspan 때문에 인덱스가 밀릴 수 있어 이 방식이 안전)
- 식사 행: 첫 셀 텍스트에 `중식`/`석식` 포함 여부로 판별 (교직원 페이지는 중식만 사용)
- 셀 내부: `<br>`로 줄 구분. `정식-5,000원` / `일품-5,000원` / `특정식-...` 헤더 줄이
  나오면 새 섹션 시작, 이후 줄들은 그 섹션의 메뉴 아이템

## 3. TS 이식본 (cheerio 사용 — `npm i cheerio`)

```ts
// lib/pnuMenu.ts — 파싱부 (프론트 pnu_menu_service.dart 검증 로직 이식)
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
    const label = $(cells[0]).text();
    const isLunch = label.includes('중식');
    const isDinner = label.includes('석식');
    if (!isLunch && !isDinner) return;
    if (staff && !isLunch) return;

    for (const [idx, date] of dates) {
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
```

```ts
// app/api/cron/menus/route.ts — 크론 엔드포인트 뼈대
import { NextResponse } from 'next/server';
import { parseBuildingWeek } from '@/lib/pnuMenu';

const STUDENT_URL =
  'https://www.pusan.ac.kr/kor/CMS/MenuMgr/menuListOnBuilding.do' +
  '?mCode=MN202&campus_gb=PUSAN&building_gb=R001&restaurant_code=PG002';
const STAFF_URL =
  'https://www.pusan.ac.kr/kor/CMS/MenuMgr/menuListOnBuilding.do?mCode=MN202';

export async function GET(req: Request) {
  // Vercel Cron 인증 (임의 호출 방지)
  if (req.headers.get('authorization') !== `Bearer ${process.env.CRON_SECRET}`) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 });
  }

  const [studentHtml, staffHtml] = await Promise.all([
    fetch(STUDENT_URL).then((r) => r.text()),
    fetch(STAFF_URL).then((r) => r.text()),
  ]);
  const student = parseBuildingWeek(studentHtml, false); // 중식+석식
  const staff = parseBuildingWeek(staffHtml, true); // 중식만

  // TODO(조우진): menus 테이블 upsert — 스키마 주인이 마무리
  // 참고: 앱은 menus를 restaurant_id + menu_date로 조회하고
  //       name(메뉴명)·price를 읽음 (lib/data/supabase/supabase_repositories.dart)
  // 제안 매핑: 섹션(정식/일품)별로 name="정식: 흑미밥, 육개장, ..." price=5000
  //           또는 품목별 행 — 현재 앱은 첫 행 price만 쓰므로 어느 쪽이든 동작
  // upsert 키: (restaurant_id, menu_date[, name]) — 중복 실행 안전하게

  return NextResponse.json({
    studentDays: student.length,
    staffDays: staff.length,
  });
}
```

```json
// vercel.json — 매주 월요일 아침 7시(KST) = 일요일 22:00 UTC
{
  "crons": [{ "path": "/api/cron/menus", "schedule": "0 22 * * 0" }]
}
```

## 4. 검증 방법

1. 로컬에서 `curl -H "Authorization: Bearer $CRON_SECRET" localhost:3000/api/cron/menus`
   → `studentDays: 5~6, staffDays: 5~6`이면 파싱 성공
2. 파싱 결과 샘플이 프론트 내장 데이터(`assets/data/kumjung_week_menu.json`)와
   같은 주면 값이 일치해야 함 (정식 5,000원 / 교직원 6,500원)
3. menus 테이블에 들어가면 **웹 배포판에서도 실식단이 뜨는지** 프론트가 확인해줌

## 5. 주의

- 방학엔 조식 미운영·석식 축소 등으로 빈 셀이 흔함 — 빈 섹션은 그냥 스킵 (코드가 이미 그렇게 동작)
- 페이지 구조가 바뀌면 헤더 행 탐지(날짜 2개 이상)부터 실패함 → 크론 응답의
  days 수가 0이면 알림 주기 (프론트 쪽 파서도 같은 방식이라 같이 고치면 됨)
