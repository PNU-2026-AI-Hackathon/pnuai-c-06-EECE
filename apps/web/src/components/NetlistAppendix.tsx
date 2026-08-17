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
        <ul className="divide-y divide-hair border border-hair">
          {netlist.nets.map((net) => (
            <li key={net.name} className="px-3 py-2">
              <div className="flex items-baseline gap-2">
                <span className="data font-semibold">{net.name}</span>
                <span className="data text-graphite">{net.connections.length}</span>
                {net.vias > 0 && <span className="data text-graphite">via {net.vias}</span>}
              </div>
              <p className="data break-words text-graphite">
                {net.connections.map((c) => `${c.ref}.${c.pin}`).join(", ")}
              </p>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <p className="label mb-2">부품 {netlist.parts.length}</p>
        <ul className="divide-y divide-hair border border-hair">
          {netlist.parts.map((part) => (
            <li key={part.ref} className="px-3 py-2">
              <div className="flex items-baseline gap-2">
                <span className="data font-semibold">{part.ref}</span>
                <span className="data text-graphite">{part.pins.length}핀</span>
                <span className="data ml-auto text-graphite">
                  {part.mpn ?? "부품번호 미상"}
                </span>
              </div>
              <p className="data break-words text-graphite">{part.pins.join(", ")}</p>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
