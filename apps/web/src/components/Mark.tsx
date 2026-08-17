/**
 * 화면 전체를 관통하는 한 가지 표기법.
 *
 *   채운 점 ● = 우리가 실제로 읽은 것
 *   빈 고리 ○ = 아직 모르는 것
 *
 * 업로드 슬롯 · 입력 표 · 발견 카드의 소스 레인이 전부 같은 기호를 쓴다.
 * 사용자가 한 번 배우면 세 화면에서 다시 배우지 않아도 된다.
 */
export function SourceMark({ known }: { known: boolean }) {
  return (
    <span
      aria-hidden
      className={`inline-block h-[10px] w-[10px] shrink-0 rounded-full ${
        known ? "bg-ink" : "border-[1.5px] border-mute bg-transparent"
      }`}
    />
  );
}

/**
 * 점에서 아래로 이어지는 세로 레일.
 * 실선이면 사실이 이어진다는 뜻, 점선이면 그 구간을 못 봤다는 뜻이다.
 */
export function SourceRail({ known }: { known: boolean }) {
  return (
    <span
      aria-hidden
      className={`absolute bottom-0 left-[4px] top-4 border-l-[1.5px] ${
        known ? "border-ink/20" : "border-dashed border-line"
      }`}
    />
  );
}
