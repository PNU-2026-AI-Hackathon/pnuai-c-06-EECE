import type { Net, NetConnection } from "../types/api";

/**
 * 네트 레일 — 이 화면의 시그니처.
 *
 * 네트는 "이 핀들은 전기적으로 같은 점"이라는 뜻이다. 그래서 도체 한 줄로 그린다.
 * 발견에 걸린 핀은 구리로, 나머지는 조용히 둔다.
 *
 * 도체가 끊겨 있으면 어긋난 것이고, 점선이면 아직 프로브를 못 댄 것이다.
 * 둘은 다른 상태이며 화면에서도 달라야 한다.
 */

/** 발견의 근거에서 언급된 핀들 — "U2.OUT" 같은 토큰에서 뽑는다 */
export function implicatedPins(highlights: string[]): Set<string> {
  const pins = new Set<string>();
  for (const token of highlights) {
    if (token.includes(".")) pins.add(token);
  }
  return pins;
}

function Tap({
  connection,
  hot,
  side,
}: {
  connection: NetConnection;
  /** 발견에 걸린 핀인지 */
  hot: boolean;
  side: "top" | "bottom";
}) {
  return (
    <div className={`flex min-w-0 flex-col items-center ${side === "top" ? "" : "flex-col-reverse"}`}>
      <span
        className={`data whitespace-nowrap px-1 text-[12px] ${
          hot ? "font-bold text-ink" : "text-muted"
        }`}
      >
        {connection.ref}.{connection.pin}
      </span>
      {/* 리드선 */}
      <span className={`h-3 w-px ${hot ? "bg-copper" : "bg-rule"}`} />
      {/* 패드 */}
      <span
        className={`size-[7px] rounded-full ${
          hot ? "bg-copper ring-2 ring-copper/25" : "bg-rule"
        }`}
      />
    </div>
  );
}

export function NetRail({
  net,
  hotPins,
  /** 코드 쪽 근거가 아직 없으면 오른쪽 절반을 점선으로 남긴다 */
  probedRight,
}: {
  net: Net;
  hotPins: Set<string>;
  probedRight: boolean;
}) {
  const isHot = (c: NetConnection) => hotPins.has(`${c.ref}.${c.pin}`);

  // 걸린 핀을 앞쪽에, 나머지는 뒤로. 많으면 접는다.
  const sorted = [...net.connections].sort((a, b) => Number(isHot(b)) - Number(isHot(a)));
  const shown = sorted.slice(0, 6);
  const hidden = sorted.length - shown.length;

  return (
    <div className="px-4 py-5">
      <div className="mb-1 flex items-baseline gap-2">
        <span className="data font-bold text-ink">{net.name}</span>
        <span className="eyebrow">
          핀 {net.connections.length}
          {net.vias > 0 && ` · 비아 ${net.vias}`}
        </span>
      </div>

      <div className="relative flex items-end justify-between gap-1 pt-6">
        {shown.map((c, i) => (
          <Tap key={`${c.ref}.${c.pin}-${i}`} connection={c} hot={isHot(c)} side="top" />
        ))}

        {/* 도체 본체 */}
        <div className="absolute inset-x-0 bottom-0 flex h-[6px] items-stretch">
          <div className="conductor flex-1 rounded-l-sm" />
          {/* 끊긴 지점 — 어긋남이 물리적으로 보이는 자리 */}
          <div className="relative w-6 shrink-0">
            <span className="absolute inset-y-0 left-1/2 w-px -translate-x-1/2 bg-open" />
            <span className="animate-arc absolute inset-0 bg-open/15" />
          </div>
          {probedRight ? (
            <div className="conductor flex-1 rounded-r-sm" />
          ) : (
            <div className="unprobed flex-1 self-center" style={{ height: 2 }} />
          )}
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
        <span className="eyebrow">
          {hidden > 0 ? `그 외 핀 ${hidden}개` : " "}
        </span>
        {!probedRight && (
          <span className="text-[12px] text-muted">
            오른쪽은 아직 프로브를 대지 못했습니다 — 펌웨어 필요
          </span>
        )}
      </div>
    </div>
  );
}
