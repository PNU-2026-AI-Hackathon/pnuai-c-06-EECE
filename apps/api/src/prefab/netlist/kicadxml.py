"""KiCad 회로도 넷리스트(kicadxml) 파서.

**왜 두 번째 형식을 읽는가.**

IPC-D-356 은 *제조용* 파일이다. 보드 집에 "여기 구멍 뚫고 여기 도통 검사해라" 를
알려주는 것이 목적이라 **사람이 읽는 이름을 안 싣는다.** 핀은 번호로만 오고
(`U3.14`), 부품번호도 데이터시트도 없다.

우리가 판정에 필요한 것이 정확히 그 이름이다. `GPIO8` 인 줄 알아야 플래시 핀인지
따지고, 부품번호를 알아야 데이터시트를 뒤진다. 실측으로 확인한 차이는 이렇다
(같은 보드, 오픈소스 ESP32-C3):

    부품번호   IPC-D-356   0%  │  kicadxml  100% (52/52)
    데이터시트 IPC-D-356   0%  │  kicadxml  100%
    핀 이름    IPC-D-356   0%  │  kicadxml   62% (115/183)

우리 보드가 지금까지 되던 것은 **Flux 가 IPC-D-356 에 실크 이름을 실어 주기 때문**이다.
KiCad 로 만든 보드에서는 `pinmap` 이 하나도 안 풀렸고, 그래서 R07·R08 이 통째로
침묵했다 (`_docs/규모_실험.md` B).

이 파일을 만드는 명령 —

    kicad-cli sch export netlist --format kicadxml -o board.xml board.kicad_sch

**한계를 먼저 적는다.**

회로도 넷리스트에는 **좌표가 없다.** 그래서 좌표에 기대는 것들이 안 돈다 —
헤더 기하로 실크를 복원하는 경로(`pinmap` 의 열 정렬)와 좌표 클러스터링 기반
전원 도메인 추정이다. 대신 핀 이름이 직접 오므로 그 복원 자체가 필요 없다.
좌표가 없다는 사실을 숨기지 않고 `parse_notes()` 로 내보낸다 (헌법 2-2).
"""

from __future__ import annotations

import re
from collections import OrderedDict
from xml.etree import ElementTree as ET

from .d356 import Netlist, NetlistParseError, Pad

#: `record` 칸에 남기는 표시. IPC-D-356 의 숫자 코드 자리를 대신한다.
RECORD = "SCH"

#: 부품번호가 실려 오는 필드 이름들. 도구·라이브러리마다 다르게 부른다.
#: 앞에 있는 것부터 본다 — 더 구체적인 이름이 앞이다.
MPN_FIELDS = ("MPN", "Manufacturer_Part_Number", "PartNumber", "Part Number", "LCSC")

#: KiCad 심볼 라이브러리는 핀 이름 끝에 핀 번호를 붙여 두는 일이 잦다
#: (`GPIO3_8` = 기능 GPIO3, 8번 핀). 실측한 두 저장소 모두 100% 이 규약이었다.
#: **번호와 정확히 맞을 때만** 뗀다. 아니면 이름을 그대로 둔다 —
#: 규약이 다른 도구에서 이름 끝을 잘라먹지 않기 위해서다.
def strip_pin_number(name: str, pin: str) -> str:
    """`GPIO3_8` + 핀 `8` → `GPIO3`. 안 맞으면 그대로."""
    suffix = f"_{pin}"
    if pin and name.endswith(suffix) and len(name) > len(suffix):
        return name[: -len(suffix)]
    return name


class Part:
    """회로도가 말해 주는 부품 하나. IPC-D-356 에는 이 정보가 통째로 없다."""

    __slots__ = ("ref", "value", "mpn", "datasheet", "footprint")

    def __init__(
        self,
        ref: str,
        value: str | None = None,
        mpn: str | None = None,
        datasheet: str | None = None,
        footprint: str | None = None,
    ) -> None:
        self.ref = ref
        self.value = value
        self.mpn = mpn
        self.datasheet = datasheet
        self.footprint = footprint


class SchematicNetlist(Netlist):
    """`Netlist` 그대로에 부품 정보를 얹은 것.

    규칙은 `Netlist` 만 알면 된다. 부품 정보는 부품 식별 단계가 쓴다.
    """

    #: 회로도 넷리스트는 이름을 안 자른다. IPC-D-356 의 14자 칸 경고를 그대로
    #: 물려받으면 `Net-(U3-LNA_IN)` 같은 멀쩡한 이름을 "잘렸을 수 있다"고 말한다.
    NAME_IS_WIDTH_LIMITED = False

    def __init__(self, *args, components: "OrderedDict[str, Part] | None" = None, **kwargs):
        super().__init__(*args, **kwargs)
        #: refdes → 회로도가 아는 부품 정보
        self.components = components or OrderedDict()

    def parse_notes(self) -> list[str]:
        notes = super().parse_notes()
        # 좌표가 없다는 것은 결함이 아니라 형식의 성질이다. 다만 조용히 넘기지 않는다.
        notes.append("회로도 넷리스트 — 좌표 없음 (기하 기반 실크 복원·전원 도메인 추정 불가)")
        with_mpn = sum(1 for c in self.components.values() if c.mpn)
        if self.components:
            notes.append(f"회로도가 실어 준 부품 {len(self.components)}개 · 부품번호 {with_mpn}개")
        return notes


def _field(comp: ET.Element, *names: str) -> str | None:
    """부품의 필드 하나를 이름으로 찾는다. 대소문자를 안 가린다."""
    lowered = {n.lower() for n in names}
    for f in comp.iterfind("./fields/field"):
        if (f.get("name") or "").lower() in lowered and f.text:
            return f.text.strip()
    return None


def _components(root: ET.Element) -> "OrderedDict[str, Part]":
    out: "OrderedDict[str, Part]" = OrderedDict()
    for comp in root.iterfind("./components/comp"):
        ref = comp.get("ref")
        if not ref:
            continue
        mpn = None
        for name in MPN_FIELDS:
            mpn = _field(comp, name)
            if mpn:
                break
        out[ref] = Part(
            ref=ref,
            value=(comp.findtext("value") or "").strip() or None,
            mpn=mpn,
            datasheet=_field(comp, "Datasheet") or (comp.findtext("datasheet") or "").strip() or None,
            footprint=(comp.findtext("footprint") or "").strip() or None,
        )
    return out


def parse_text(text: str, filename: str = "") -> SchematicNetlist:
    """kicadxml 한 덩어리를 `Netlist` 로.

    좌표는 없다. `Pad.x`·`Pad.y` 는 전부 None 이고, 그래서 `net_at()` 은
    `net_of()` 와 같아진다 — 회로도에서는 핀 번호가 부품 안에서 유일하므로
    좌표 없이도 패드가 하나로 정해진다.
    """
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise NetlistParseError(f"XML 로 읽을 수 없습니다: {exc}") from exc

    if root.tag != "export":
        raise NetlistParseError(
            f"kicadxml 이 아닙니다 (최상위 태그가 <{root.tag}>). "
            "`kicad-cli sch export netlist --format kicadxml` 로 뽑은 파일이어야 합니다."
        )

    nets: "OrderedDict[str, list[Pad]]" = OrderedDict()
    parts: "OrderedDict[str, set[str]]" = OrderedDict()

    for net in root.iterfind("./nets/net"):
        name = (net.get("name") or "").strip()
        pads: list[Pad] = []
        for node in net.iterfind("./node"):
            ref, pin = node.get("ref"), (node.get("pin") or "").strip()
            if not ref:
                continue
            fn = (node.get("pinfunction") or "").strip()
            pads.append(
                Pad(
                    ref=ref,
                    pin=pin,
                    record=RECORD,
                    name=strip_pin_number(fn, pin) if fn else None,
                )
            )
            parts.setdefault(ref, set()).add(pin)
        if pads:
            nets.setdefault(name, []).extend(pads)

    if not nets:
        raise NetlistParseError("네트가 하나도 없습니다.")

    return SchematicNetlist(
        nets=nets,
        parts=parts,
        meta=[],
        filename=filename,
        components=_components(root),
    )
