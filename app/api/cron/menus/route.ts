import { NextResponse } from 'next/server';
import { parseBuildingWeek, type DayMenu } from '@/lib/pnuMenu';
import { supabaseAdmin } from '@/lib/supabase/server';

/**
 * GET /api/cron/menus — 주 1회(월요일 아침) 부산대 주간 식단을 수집해 menus 테이블에 반영.
 * Vercel Cron이 Authorization: Bearer <CRON_SECRET> 로 호출한다.
 */
const STUDENT_URL =
  'https://www.pusan.ac.kr/kor/CMS/MenuMgr/menuListOnBuilding.do' +
  '?mCode=MN202&campus_gb=PUSAN&building_gb=R001&restaurant_code=PG002';
const STAFF_URL =
  'https://www.pusan.ac.kr/kor/CMS/MenuMgr/menuListOnBuilding.do?mCode=MN202';

// 시드로 만든 금정회관 학생식당 id
const STUDENT_RESTAURANT_ID = 'a0000000-0000-0000-0000-000000000001';
// 교직원식당을 별도 restaurants 행으로 만들면 그 id를 env에 넣으면 수집됨(없으면 건너뜀)
const STAFF_RESTAURANT_ID = process.env.STAFF_RESTAURANT_ID ?? '';

type Row = {
  restaurant_id: string;
  menu_date: string;
  name: string;
  price: number;
  description: string;
};

function toRows(days: DayMenu[], restaurantId: string, includeDinner: boolean): Row[] {
  const rows: Row[] = [];
  for (const d of days) {
    const push = (meal: string, sections: DayMenu['lunch']) => {
      for (const s of sections) {
        rows.push({
          restaurant_id: restaurantId,
          menu_date: d.date,
          name: `${meal} ${s.name}`, // 예: "중식 정식"
          price: s.price,
          description: s.items.join(', '),
        });
      }
    };
    push('중식', d.lunch);
    if (includeDinner) push('석식', d.dinner);
  }
  return rows;
}

async function replaceWeek(restaurantId: string, rows: Row[], dates: string[]) {
  if (!restaurantId || !dates.length) return 0;
  // 해당 주 날짜의 기존 메뉴 삭제 후 재삽입 → 재실행해도 중복 안 생김
  await supabaseAdmin
    .from('menus')
    .delete()
    .eq('restaurant_id', restaurantId)
    .in('menu_date', dates);
  if (rows.length) {
    const { error } = await supabaseAdmin.from('menus').insert(rows);
    if (error) throw error;
  }
  return rows.length;
}

export async function GET(req: Request) {
  // Vercel Cron 인증 (임의 호출 방지)
  if (req.headers.get('authorization') !== `Bearer ${process.env.CRON_SECRET}`) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 });
  }

  try {
    const [studentHtml, staffHtml] = await Promise.all([
      fetch(STUDENT_URL).then((r) => r.text()),
      fetch(STAFF_URL).then((r) => r.text()),
    ]);

    const student = parseBuildingWeek(studentHtml, false); // 중식+석식
    const staff = parseBuildingWeek(staffHtml, true); // 중식만

    const studentRows = toRows(student, STUDENT_RESTAURANT_ID, true);
    const insertedStudent = await replaceWeek(
      STUDENT_RESTAURANT_ID,
      studentRows,
      student.map((d) => d.date),
    );

    let insertedStaff = 0;
    if (STAFF_RESTAURANT_ID) {
      const staffRows = toRows(staff, STAFF_RESTAURANT_ID, false);
      insertedStaff = await replaceWeek(
        STAFF_RESTAURANT_ID,
        staffRows,
        staff.map((d) => d.date),
      );
    }

    return NextResponse.json({
      studentDays: student.length,
      staffDays: staff.length,
      insertedStudent,
      insertedStaff,
    });
  } catch (e) {
    return NextResponse.json(
      { error: 'cron failed', message: e instanceof Error ? e.message : String(e) },
      { status: 500 },
    );
  }
}
