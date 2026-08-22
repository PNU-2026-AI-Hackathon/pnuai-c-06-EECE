"""제안 → 검증을 잇는다. **분석 결과에서 검증에 필요한 것을 꺼내 오는 자리.**"""

from __future__ import annotations

from .propose import propose
from .types import Proposal
from .verify import verify


def covered_places(findings) -> "set[tuple[str, str]]":
    """기존 규칙이 이미 발견을 낸 자리 `(부품, 핀)`.

    근거에 찍힌 `U1.D5` 같은 토큰에서 읽는다. 여기가 비면 후보 검증이 느슨해지지만
    **틀린 자리를 지어내지는 않는다** — 못 읽으면 그냥 안 거를 뿐이다.
    """
    out: "set[tuple[str, str]]" = set()
    for f in findings:
        for e in f.evidence:
            if e.kind != "netlist":
                continue
            for token in e.highlight or ():
                if "." in token:
                    ref, _, pin = token.partition(".")
                    out.add((ref.strip(), pin.strip()))
    return out


def netlist_parts(netlist) -> "dict[str, set[str]]":
    """부품기호 → 그 부품이 가진 핀 이름들. 후보가 없는 핀을 가리키면 여기서 걸린다."""
    parts: "dict[str, set[str]]" = {}
    for pads in netlist.nets.values():
        for pad in pads:
            if getattr(pad, "is_via", False):
                continue
            names = parts.setdefault(pad.ref, set())
            names.add(pad.pin)
            if pad.name:
                names.add(pad.name)
    return parts


def discover(analysis, *, netlist_text: str, firmware_sources=None, api_key=None) -> Proposal:
    """후보를 받아 검증까지 마친 결과.

    **모델을 못 불러도 예외를 던지지 않는다.** 이 기능이 안 된다고 검사가 죽으면 안 된다 —
    검사는 이미 끝났고 이건 그 위에 얹는 것이다.
    """
    from .. import catalog

    findings = analysis.engine.findings
    raw, unavailable = propose(
        netlist_text=netlist_text,
        firmware_sources=firmware_sources,
        catalog_rules=catalog.CATALOG,
        findings=findings,
        api_key=api_key,
    )
    if unavailable:
        return Proposal(unavailable=unavailable)

    result = verify(
        raw,
        firmware_sources=firmware_sources,
        netlist_parts=netlist_parts(analysis.netlist),
        covered_places=covered_places(findings),
    )
    return Proposal(
        kept=result.kept,
        dropped=result.dropped,
        notes=(
            f"모델이 {len(raw)}건을 냈고 코드가 {len(result.kept)}건을 남겼습니다.",
        ),
    )
