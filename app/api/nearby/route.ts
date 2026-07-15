import { NextResponse } from 'next/server';

/**
 * GET /api/nearby — 부산대 주변 음식점(카카오 로컬 API) 서버 프록시
 *   - 기본: 카테고리(FD6) 검색
 *   - ?q=키워드  → 키워드 검색(keyword.json)
 *   - ?page=N    → 페이지네이션 (기본 1)
 *   - radius 1200m
 * (CORS 응답 헤더는 middleware.ts가 /api/* 전체에 붙여줌)
 */
const BASE = 'https://dapi.kakao.com/v2/local/search';
const X = '129.0843';
const Y = '35.2318';
const RADIUS = '1200';

export async function GET(req: Request) {
  const key = process.env.KAKAO_REST_KEY;
  if (!key) {
    return NextResponse.json({ error: 'KAKAO_REST_KEY not set' }, { status: 500 });
  }

  const { searchParams } = new URL(req.url);
  const q = searchParams.get('q');
  const page = searchParams.get('page') ?? '1';

  const common = `x=${X}&y=${Y}&radius=${RADIUS}&size=15&page=${page}&sort=distance`;
  const url = q
    ? `${BASE}/keyword.json?query=${encodeURIComponent(q)}&category_group_code=FD6&${common}`
    : `${BASE}/category.json?category_group_code=FD6&${common}`;

  const res = await fetch(url, {
    headers: { Authorization: `KakaoAK ${key}` },
    next: { revalidate: 600 }, // 10분 캐시
  });

  if (!res.ok) {
    const body = await res.text();
    return NextResponse.json(
      { error: 'kakao request failed', status: res.status, body },
      { status: 502 },
    );
  }

  return NextResponse.json(await res.json());
}
