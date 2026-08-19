"""규칙 카탈로그 — 규칙 개수의 유일한 진실.

README·CLAUDE.md·계약 세 곳에 숫자를 손으로 적으면 반드시 어긋난다.
실제로 어긋나 있었다 (카탈로그 11개인데 응답은 12개 기준).
GET /api/v1/rules 와 summary.rules_* 는 전부 이 파일에서 계산된다.

`implemented` 는 여기 적지 않는다. rules 레지스트리에 모듈이 있으면 True 다.
"""

from __future__ import annotations

from dataclasses import dataclass

from .types import Severity, Tier


@dataclass(frozen=True)
class RuleSpec:
    id: str
    title: str
    tier: Tier
    severity: Severity
    #: 계약의 RuleInfo.needs 와 같은 어휘: netlist | bom | firmware
    needs: tuple[str, ...]
    #: 왜 아직 못 도는지. 구현된 규칙은 None.
    blocked_by: str | None = None


#: R6(I2C 풀업 누락)은 Flux Design Review 가 이미 제공하므로 폐기했다. 번호를 비워 둔다.
CATALOG: tuple[RuleSpec, ...] = (
    RuleSpec(
        "R01",
        "코드가 이 칩에서 쓸 수 없는 핀을 사용",
        "차별",
        Severity.CRITICAL,
        ("netlist", "firmware"),
    ),
    RuleSpec(
        "R02",
        "회로도가 SPI 플래시 전용 핀에 배선",
        "기본",
        Severity.CRITICAL,
        ("netlist",),
    ),
    RuleSpec(
        "R03",
        "스트래핑 핀이 전원·접지에 직결",
        "기본",
        Severity.WARNING,
        ("netlist",),
    ),
    RuleSpec(
        "R04",
        "외부 부품 출력이 GPIO 입력 최대 정격 초과",
        "기본",
        Severity.CRITICAL,
        ("netlist", "bom"),
    ),
    RuleSpec(
        "R05",
        "이 칩이 지원하지 않는 주변장치 조합",
        "차별",
        # 칩 표는 ESP32 의 ADC2+WiFi 를 CRITICAL 로 규정한다. C6 의 ADC∩스트래핑은
        # WARNING 이다. 카탈로그에는 더 무거운 쪽을 적는다.
        Severity.CRITICAL,
        # 펌웨어만으로는 안 된다 — 어느 칩인지 알아야 조합을 판정할 수 있고,
        # 칩은 넷리스트의 모듈 매칭이나 BOM 부품번호로 정한다.
        ("netlist", "firmware"),
    ),
    RuleSpec(
        "R07",
        "코드가 쓰는 핀이 회로도에 미연결",
        "차별",
        Severity.CRITICAL,
        ("netlist", "firmware"),
    ),
    RuleSpec(
        "R08",
        "회로도에 연결됐는데 코드가 초기화 안 함",
        "차별",
        Severity.WARNING,
        ("netlist", "firmware"),
    ),
    RuleSpec(
        "R09",
        "부팅 시 출력 나오는 핀에 부하 연결",
        "기본",
        Severity.WARNING,
        ("netlist",),
        "규칙 로직 미작성 — 칩 표(docs/CHIPS.md)와 pinmap 은 있다",
    ),
    RuleSpec(
        "R10",
        "회로도 변경 후 코드 미추종 (드리프트)",
        "차별",
        Severity.WARNING,
        ("netlist", "firmware"),
        "git 이력 연동 미구현 — 계약에 4번째 입력이 필요하다",
    ),
    RuleSpec(
        "R11",
        "네트명이 주장하는 전압과 소스 부품의 전원 도메인이 다름",
        "기본",
        Severity.WARNING,
        ("netlist",),
    ),
    RuleSpec(
        "R12",
        "상위 전원 도메인이 하위를 직결",
        "기본",
        Severity.CRITICAL,
        ("netlist",),
    ),
)

#: 채택 대기 중인 제안. **카탈로그가 아니다** — rules_total 에 들어가지 않는다.
#: 하드웨어 담당이 채택 판정을 내리면 그때 CATALOG 로 옮긴다.
#: 근거: tests/fixtures/esp32-c6-presence-smart-light.EXPECTED.md 「R13(신규 제안)」
PROPOSED: tuple[RuleSpec, ...] = (
    RuleSpec(
        "R13",
        "코드가 출력으로 구동하는 핀에 다른 부품 출력이 연결됨",
        "차별",
        Severity.CRITICAL,
        ("netlist", "firmware"),
        "하드웨어 담당 채택 판정 대기 — 출력 충돌이 실제 위험인지 검수 필요",
    ),
)

TOTAL = len(CATALOG)

BY_ID: dict[str, RuleSpec] = {spec.id: spec for spec in CATALOG}
