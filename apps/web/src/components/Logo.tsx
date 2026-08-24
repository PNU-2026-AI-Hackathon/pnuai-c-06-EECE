/**
 * Prefab 마크 — **끊긴 이음**.
 *
 *     ●─ ○
 *
 * 이어져 있어야 하는데 끊긴 자리. 이 제품이 하는 일 그 자체다.
 *
 * ## 새로 만든 기호가 아니다
 *
 * 화면이 이미 이 표기법을 쓰고 있다 (`Mark.tsx`) —
 * **채운 점은 읽은 것, 빈 고리는 모르는 것.** 업로드 슬롯 · 입력 표 · 발견 카드의
 * 소스 레인이 전부 같은 기호다. 로고를 여기서 꺼내면 사용자가 한 번 배운 것을
 * 다시 배우지 않아도 된다.
 *
 * ## 그리는 규칙
 *
 * - **순수 기하만.** 원과 선뿐이다. 그라데이션·일러스트는 이 프로젝트 범위 밖이다
 *   (`apps/web/CLAUDE.md` 6절)
 * - **`currentColor` 를 쓴다.** 글자 색을 그대로 따라가므로 헤더·인쇄·다크 모드에
 *   같은 파일 하나로 대응한다. 색을 박으면 그때마다 변형이 는다
 * - **작은 크기에서 선을 굵게 한다.** 16px 에서 2.6 은 뭉개진다. `small` 이 그 몫이다
 */
export function Logo({
  size = 24,
  small = false,
  className = "",
}: {
  size?: number;
  /** 16px 이하에서 켠다 — 선을 굵히고 간격을 벌린다 */
  small?: boolean;
  className?: string;
}) {
  const stroke = small ? 3 : 2.6;
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      className={className}
      aria-hidden="true"
      focusable="false"
    >
      {/* 읽은 것 — 채운 점 */}
      <circle cx="7" cy="16" r={small ? 4.4 : 4} fill="currentColor" />
      {/* 이음 — 여기서 끊긴다 */}
      <path d="M13 16 H17" stroke="currentColor" strokeWidth={stroke} strokeLinecap="round" />
      {/* 모르는 것 — 빈 고리 */}
      <circle
        cx="25"
        cy="16"
        r={small ? 3.6 : 3.4}
        fill="none"
        stroke="currentColor"
        strokeWidth={stroke}
      />
    </svg>
  );
}
