import { supabaseAdmin } from '@/lib/supabase/server';

/**
 * 요청 헤더의 `Authorization: Bearer <Supabase accessToken>`을 검증해
 * 로그인 사용자를 반환한다. 토큰이 없거나 유효하지 않으면 null.
 */
export async function getUser(req: Request) {
  const h = req.headers.get('authorization') ?? '';
  const token = h.startsWith('Bearer ') ? h.slice(7) : '';
  if (!token) return null;
  const { data, error } = await supabaseAdmin.auth.getUser(token);
  return error ? null : data.user;
}
