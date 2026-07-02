import { NextResponse } from 'next/server';
import { supabaseAdmin } from '@/lib/supabase/server';

export async function GET() {
  const { error } = await supabaseAdmin.from('users').select('id').limit(1);
  return NextResponse.json({ db: error ? 'fail' : 'ok', error: error?.message });
}