/**
 * 화면 전체를 관통하는 한 가지 표기법.
 *
 *   ● read     읽었고 근거가 있다
 *   ◍ none     소스는 받았는데 이 판정에는 근거로 쓰이지 않았다
 *   ○ unknown  소스 자체가 없어서 모른다
 *
 * `none` 과 `unknown` 을 구분하는 게 중요하다.
 * 펌웨어를 읽고도 "펌웨어를 올려주세요"라고 말하면 그건 거짓말이다.
 *
 * 업로드 슬롯 · 입력 표 · 발견 카드의 소스 레인이 전부 같은 기호를 쓴다.
 */
export type SourceState = "read" | "none" | "unknown";

const MARK: Record<SourceState, string> = {
  read: "bg-ink",
  none: "border-[1.5px] border-ink bg-transparent",
  unknown: "border-[1.5px] border-mute bg-transparent",
};

export function SourceMark({ state }: { state: SourceState }) {
  return (
    <span
      aria-hidden
      className={`inline-block h-[10px] w-[10px] shrink-0 rounded-full ${MARK[state]}`}
    />
  );
}

/**
 * 점에서 아래로 이어지는 세로 레일.
 * 소스를 갖고 있으면 실선, 소스 자체가 없으면 점선이다.
 */
export function SourceRail({ state }: { state: SourceState }) {
  return (
    <span
      aria-hidden
      className={`absolute bottom-0 left-[4px] top-4 border-l-[1.5px] ${
        state === "unknown" ? "border-dashed border-line" : "border-ink/20"
      }`}
    />
  );
}
