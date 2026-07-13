import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * /api/* 응답에 CORS 헤더를 붙이고, 브라우저 프리플라이트(OPTIONS)를 처리한다.
 * (Flutter 웹 빌드에서 API를 호출할 때 필요)
 */
function corsHeaders(origin: string): Record<string, string> {
  return {
    'Access-Control-Allow-Origin': origin,
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    'Access-Control-Max-Age': '86400',
  };
}

export function middleware(req: NextRequest) {
  const origin = req.headers.get('origin') ?? '*';

  if (req.method === 'OPTIONS') {
    return new NextResponse(null, { status: 204, headers: corsHeaders(origin) });
  }

  const res = NextResponse.next();
  for (const [k, v] of Object.entries(corsHeaders(origin))) {
    res.headers.set(k, v);
  }
  return res;
}

export const config = { matcher: '/api/:path*' };
