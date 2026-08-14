/** 화면 표시용 포맷 헬퍼. 숫자 자체를 가공하지 않고 표기만 담당한다 */

/** 원화 금액을 "3,261,000원"으로 */
export function formatWon(value: number): string {
  return `${value.toLocaleString("ko-KR")}원`;
}

/** 원화 금액을 "326만원" 수준으로 축약 (차트 축·요약 카드용) */
export function formatWonShort(value: number): string {
  if (Math.abs(value) >= 10000) return `${Math.round(value / 10000).toLocaleString("ko-KR")}만원`;
  return `${value.toLocaleString("ko-KR")}원`;
}

/** 증감률을 "+5.6%" / "-3.0%"로 (부호 항상 표시) */
export function formatChangeRate(value: number): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(1)}%`;
}

/** 요일 번호(0=일)를 한글 한 글자로 */
export function weekdayLabel(weekday: number): string {
  return ["일", "월", "화", "수", "목", "금", "토"][weekday] ?? "?";
}

/** "2026-10-12" → "10/12(월)". 시각이 붙은 값("...T18:00:00")도 그대로 받는다 */
export function formatDateShort(date: string): string {
  const d = new Date(`${date.slice(0, 10)}T00:00:00`);
  return `${d.getMonth() + 1}/${d.getDate()}(${weekdayLabel(d.getDay())})`;
}

/** "2026-10-18T20:00:00" → "10/18(일) 저녁 8시" */
export function formatDateTimeShort(dateTime: string): string {
  const hour = Number(dateTime.slice(11, 13));
  const minute = Number(dateTime.slice(14, 16));
  const period = hour < 12 ? "오전" : hour < 18 ? "오후" : "저녁";
  const hour12 = hour % 12 === 0 ? 12 : hour % 12;
  const time = minute === 0 ? `${hour12}시` : `${hour12}시 ${minute}분`;
  return `${formatDateShort(dateTime)} ${period} ${time}`;
}

/** 기간을 "2026.10.12 ~ 10.18"로 */
export function formatPeriod(start: string, end: string): string {
  const s = start.replaceAll("-", ".");
  const e = end.slice(5).replaceAll("-", ".");
  return `${s} ~ ${e}`;
}

/** 신뢰 수준을 한글 라벨로 */
export function confidenceLabel(level: "high" | "medium" | "low"): string {
  return { high: "신뢰도 높음", medium: "신뢰도 보통", low: "신뢰도 낮음" }[level];
}
