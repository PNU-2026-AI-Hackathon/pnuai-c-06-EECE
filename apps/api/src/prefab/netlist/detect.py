"""넷리스트 형식 감지 — 어느 파서로 읽을지 정한다.

**확장자를 안 믿는다.** 사용자는 파일 이름을 바꾼다. 실제로 우리 계약이 허용하는
`.txt` 는 둘 다일 수 있고, KiCad 가 내는 `.xml` 을 `.net` 으로 저장해 올릴 수도 있다.
**내용의 첫 글자가 형식을 말한다** — 그것만 본다.

읽을 수 있는 두 가지:

    IPC-D-356   제조용. 고정폭. 핀 이름이 4자에서 잘리고 부품번호가 없다
    kicadxml    회로도용. 핀 이름이 안 잘리고 부품번호·데이터시트가 함께 온다

둘 다 `Netlist` 로 나오므로 규칙은 어느 쪽인지 모른다. 아는 것은 파이프라인뿐이고,
파이프라인은 그걸 화면에 그대로 적는다 (헌법 2-4).
"""

from __future__ import annotations

from . import d356, kicadxml
from .d356 import Netlist, NetlistParseError

#: 형식 id → 사람이 읽는 이름. 파이프라인과 오류 문구가 같이 쓴다.
FORMAT_NAMES = {
    "d356": "IPC-D-356",
    "kicadxml": "KiCad 회로도 넷리스트",
}

#: XML 로 볼 첫 글자. BOM·공백을 벗긴 뒤에 본다.
_XML_STARTS = ("<?xml", "<export")


def detect(text: str) -> str:
    """형식 id 를 돌려준다. 모르면 `d356` 으로 본다 (기존 동작).

    IPC-D-356 은 `P  CODE`·`P  UNITS` 헤더나 `317`·`327` 레코드로 시작한다.
    XML 은 꺾쇠로 시작한다. 그 둘은 첫 글자에서 갈린다.
    """
    head = text.lstrip("﻿ \t\r\n")[:64].lower()
    return "kicadxml" if head.startswith(_XML_STARTS) else "d356"


def parse_any(text: str, filename: str = "") -> Netlist:
    """형식을 감지해서 읽는다. 두 파서 모두 `Netlist` 를 낸다.

    XML 로 보이는데 kicadxml 이 아니면 **d356 으로 되돌리지 않는다.**
    그러면 "레코드 0줄" 같은 엉뚱한 오류가 나서 사용자가 진짜 원인을 못 찾는다.
    무엇이 잘못됐는지 그대로 올린다.
    """
    if detect(text) == "kicadxml":
        return kicadxml.parse_text(text, filename=filename)
    return d356.parse_text(text, filename=filename)


def format_of(netlist: Netlist) -> str:
    """이미 읽은 넷리스트가 어느 형식이었는지."""
    return "kicadxml" if isinstance(netlist, kicadxml.SchematicNetlist) else "d356"


__all__ = ["detect", "parse_any", "format_of", "FORMAT_NAMES", "NetlistParseError"]
