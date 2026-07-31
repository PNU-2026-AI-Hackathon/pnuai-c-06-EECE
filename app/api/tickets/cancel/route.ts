import { NextResponse } from 'next/server';
import { supabaseAdmin } from '@/lib/supabase/server';
import { getUser } from '@/lib/auth';

/**
 * POST /api/tickets/cancel — 식권 취소
 * 요청: { ticketId }
 * 응답: { ok, status } 또는 { ok:false, reason }
 * 본인 소유 + status='paid'인 티켓만 취소 → status='canceled'
 * (동시성/검증은 DB 함수 cancel_ticket에서 처리)
 */
export async function POST(req: Request) {
  const user = await getUser(req);
  if (!user) return NextResponse.json({ error: 'unauthorized' }, { status: 401 });

  const { ticketId } = await req.json();
  if (!ticketId) {
    return NextResponse.json({ error: 'ticketId required' }, { status: 400 });
  }

  const { data, error } = await supabaseAdmin.rpc('cancel_ticket', {
    p_ticket: ticketId,
    p_user: user.id,
  });
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });

  return NextResponse.json(data);
}
