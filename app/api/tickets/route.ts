import { NextResponse } from 'next/server';
import { supabaseAdmin } from '@/lib/supabase/server';
import { getUser } from '@/lib/auth';

/**
 * POST /api/tickets  — 식권 구매 = 대기열 등록
 * 요청: { diningLineId }
 * 응답: { ticketId, qrToken, queueCount }
 * (동시성/중복은 DB 함수 purchase_ticket에서 원자적으로 처리)
 */
export async function POST(req: Request) {
  const user = await getUser(req);
  if (!user) return NextResponse.json({ error: 'unauthorized' }, { status: 401 });

  const { diningLineId } = await req.json();
  if (!diningLineId) {
    return NextResponse.json({ error: 'diningLineId required' }, { status: 400 });
  }

  const { data, error } = await supabaseAdmin.rpc('purchase_ticket', {
    p_line: diningLineId,
    p_user: user.id,
  });
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });

  return NextResponse.json(data);
}
