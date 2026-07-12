import { NextResponse } from 'next/server';
import { supabaseAdmin } from '@/lib/supabase/server';
import { getUser } from '@/lib/auth';

/**
 * POST /api/tickets/verify  — 운영자 QR 검증 + 자동 호출
 * 요청: { qrToken }
 * 응답: { valid, status }
 * 배식 완료 처리 후, 같은 라인의 다음 대기 티켓을 'called'로 전이(자동 호출).
 */
export async function POST(req: Request) {
  const user = await getUser(req);
  if (!user) return NextResponse.json({ error: 'unauthorized' }, { status: 401 });

  const { qrToken } = await req.json();
  if (!qrToken) {
    return NextResponse.json({ error: 'qrToken required' }, { status: 400 });
  }

  const { data, error } = await supabaseAdmin.rpc('verify_ticket', { p_qr: qrToken });
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });

  return NextResponse.json(data);
}
