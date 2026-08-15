import { NextResponse } from "next/server";

import academicCalendar from "@/data/academic-calendar.json";
import { analyzeSales, type AcademicCalendar } from "@/lib/analysis";
import { clearAnalysis, saveAnalysis } from "@/lib/analysis/session-store";

/**
 * 사장님이 올린 CSV를 분석해 서버 메모리에 담아 둔다.
 * 백엔드가 생기면 이 라우트가 `POST /stores/{id}/uploads` 로 대체된다 — 응답 모양은 그대로다.
 */

/** 사장님이 실수로 올릴 만한 크기까지만 받는다 (1년치 결제 내역이 대략 3~5MB) */
const MAX_BYTES = 20 * 1024 * 1024;

export async function POST(request: Request) {
  const form = await request.formData();
  const file = form.get("file");
  const storeName = String(form.get("storeName") ?? "").trim();

  if (!(file instanceof File)) {
    return NextResponse.json({ detail: "파일이 오지 않았습니다. 다시 올려주세요." }, { status: 400 });
  }
  if (file.size === 0) {
    return NextResponse.json({ detail: "빈 파일입니다. 내용이 있는 파일을 올려주세요." }, { status: 400 });
  }
  if (file.size > MAX_BYTES) {
    return NextResponse.json(
      { detail: "파일이 20MB를 넘습니다. 기간을 나눠서 올려주세요." },
      { status: 413 }
    );
  }

  let result;
  try {
    result = analyzeSales({
      csvText: await file.text(),
      fileName: file.name,
      calendar: academicCalendar as AcademicCalendar,
      store: {
        id: "store_uploaded",
        name: storeName || file.name.replace(/\.[^.]+$/, ""),
        category: "pub",
      },
      // 기준 시점을 주지 않는다 — 파일의 마지막 날짜가 곧 "오늘"이다
      today: null,
    });
  } catch (error) {
    // 파싱 실패 메시지는 사장님이 읽어도 되는 문장으로 만들어 두었다
    const detail = error instanceof Error ? error.message : "파일을 읽지 못했습니다.";
    return NextResponse.json({ detail }, { status: 422 });
  }

  if (!result.ok) {
    // 파일은 읽었지만 분석까지는 못 갔다. 화면은 기본 데이터로 두고 이유만 돌려준다.
    clearAnalysis();
    return NextResponse.json({ ok: false, reason: result.reason, upload: result.upload });
  }

  saveAnalysis(result);
  return NextResponse.json({ ok: true, upload: result.upload, meta: result.meta });
}

/** 업로드한 데이터를 지우고 기본 시연 데이터로 돌아간다 */
export async function DELETE() {
  clearAnalysis();
  return NextResponse.json({ ok: true });
}
