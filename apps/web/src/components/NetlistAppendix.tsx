import type { CheckResult, NetConnection, Part } from "../types/api";

/**
 * 우리가 파일을 어떻게 읽었는지 그대로 펼쳐 놓는다.
 * 판정을 못 믿겠으면 여기서 직접 확인할 수 있어야 한다.
 *
 * **파일에 적힌 것과 우리가 추론한 것을 둘 다 보여준다.**
 * `SDIO` 는 넷리스트에 있는 그대로이고 4자에서 잘려 있다.
 * `D5` 는 좌표로 우리가 알아낸 것이다. 추론으로 원본을 덮으면 부록의 존재 이유가 사라진다.
 */

/**
 * `U1.D5(SDIO)` — 실크를 모르면 `U1.SDIO`.
 * 실크와 파일의 이름이 같으면(`3V3`) 괄호를 붙이지 않는다. 같은 말을 두 번 하지 않는다.
 */
function padLabel(c: NetConnection): string {
  if (!c.silk) return `${c.ref}.${c.pin}`;
  if (c.silk === c.pin) return `${c.ref}.${c.silk}`;
  return `${c.ref}.${c.silk}(${c.pin})`;
}

/** 실크가 확정된 패드가 몇 개인지. 없으면 null — 개수를 지어내지 않는다 */
function resolved(part: Part): string[] | null {
  const silks = (part.pads ?? []).filter((p) => p.silk).map((p) => p.silk as string);
  return silks.length > 0 ? silks : null;
}

export function NetlistAppendix({ netlist }: { netlist: CheckResult["netlist"] }) {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <section>
        <p className="label mb-2">네트 {netlist.nets.length}</p>
        <ul className="card divide-y divide-line overflow-hidden">
          {netlist.nets.map((net) => (
            <li key={net.name} className="px-4 py-3">
              <div className="flex items-baseline gap-2">
                <span className="data font-semibold">{net.name}</span>
                <span className="data text-mute">{net.connections.length}</span>
                {net.vias > 0 && <span className="data text-mute">via {net.vias}</span>}
              </div>
              <p className="data mt-0.5 break-words text-sub">
                {net.connections.map(padLabel).join(", ")}
              </p>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <p className="label mb-2">부품 {netlist.parts.length}</p>
        <ul className="card divide-y divide-line overflow-hidden">
          {netlist.parts.map((part) => {
            const silks = resolved(part);
            return (
              <li key={part.ref} className="px-4 py-3">
                <div className="flex items-baseline gap-2">
                  <span className="data font-semibold">{part.ref}</span>
                  <span className="data text-mute">{part.pins.length}핀</span>
                  <span className="data ml-auto text-mute">{part.mpn ?? "부품번호 미상"}</span>
                </div>
                <p className="data mt-0.5 break-words text-sub">{part.pins.join(", ")}</p>
                {/*
                  넷리스트가 4자에서 자르는 바람에 위 줄에서는 D3·D4·D5 가 SDIO 하나로 보인다.
                  좌표로 되살린 실크 라벨을 따로 적는다. 못 되살린 부품에는 이 줄이 아예 없다.
                */}
                {silks && (
                  <p className="mt-1.5 flex flex-wrap items-baseline gap-x-1.5 text-[12px] text-mute">
                    <span>좌표로 확정한 실크 {silks.length}</span>
                    <span className="data text-sub">{silks.join(" · ")}</span>
                  </p>
                )}
              </li>
            );
          })}
        </ul>
      </section>
    </div>
  );
}
