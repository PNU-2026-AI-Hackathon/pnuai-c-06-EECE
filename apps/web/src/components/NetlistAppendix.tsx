import type { CheckResult } from "../types/api";

/**
 * 우리가 파일을 어떻게 읽었는지 그대로 펼쳐 놓는다.
 * 판정을 못 믿겠으면 여기서 직접 확인할 수 있어야 한다.
 */
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
                {net.connections.map((c) => `${c.ref}.${c.pin}`).join(", ")}
              </p>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <p className="label mb-2">부품 {netlist.parts.length}</p>
        <ul className="card divide-y divide-line overflow-hidden">
          {netlist.parts.map((part) => (
            <li key={part.ref} className="px-4 py-3">
              <div className="flex items-baseline gap-2">
                <span className="data font-semibold">{part.ref}</span>
                <span className="data text-mute">{part.pins.length}핀</span>
                <span className="data ml-auto text-mute">{part.mpn ?? "부품번호 미상"}</span>
              </div>
              <p className="data mt-0.5 break-words text-sub">{part.pins.join(", ")}</p>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
