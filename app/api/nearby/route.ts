import { NextResponse } from 'next/server';

/**
 * GET /api/nearby — 부산대 주변 음식점(카카오 로컬 API) 서버 프록시
 * 웹은 카카오 API가 CORS를 막아서 직접 호출 불가 → 서버가 중계한다.
 * (CORS 응답 헤더는 middleware.ts가 /api/* 전체에 붙여줌)
 */
const KAKAO_URL =
  'https://dapi.kakao.com/v2/local/search/category.json' +
  '?category_group_code=FD6&x=129.0843&y=35.2318&radius=800&size=15&sort=distance';

export async function GET() {
  const key = process.env.KAKAO_REST_KEY;
  if (!key) {
    return NextResponse.json({ error: 'KAKAO_REST_KEY not set' }, { status: 500 });
  }

  const res = await fetch(KAKAO_URL, {
    headers: { Authorization: `KakaoAK ${key}` },
    next: { revalidate: 600 }, // 10분 캐시
  });

  if (!res.ok) {
    return NextResponse.json(
      { error: 'kakao request failed', status: res.status },
      { status: 502 },
    );
  }

  return NextResponse.json(await res.json());
}
