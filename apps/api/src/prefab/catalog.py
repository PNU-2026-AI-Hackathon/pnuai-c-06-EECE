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
        # 원안(후보A)은 `정보` 였다. 커넥터와 구동 부품을 못 가르면 그게 맞다 —
        # 개발 보드는 거의 전부 TX 를 헤더로 뽑고, 그것까지 경고면 시끄럽다.
        # 규칙이 부품기호로 그 둘을 가르게 되면서 `경고` 가 됐다: 릴레이·모터가
        # 부팅 때 움직이는 것은 확인 요청이 아니라 결함이다.
        Severity.WARNING,
        ("netlist",),
    ),
    RuleSpec(
        "R10",
        "회로도 변경 후 코드 미추종 (드리프트)",
        "차별",
        # 후보A 원안대로 치명이다. 그 상태로 보드를 만들면 동작하지 않는다.
        # R07(절반)이 이미 치명이라 둘을 이은 R10 이 그보다 약할 수 없다.
        Severity.CRITICAL,
        # 이전 넷리스트는 `datasheet` 와 같은 **선택 입력**이다. 계약 어휘를 넓히지
        # 않는다 — 웹으로 파일 셋을 올리는 사람에게는 이전 상태가 없고, 있는 곳은 CI 다.
        ("netlist", "firmware"),
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
    RuleSpec(
        # 실제 오픈소스 보드에서 찾은 결함으로 만든 규칙이다. 합성 케이스로는
        # 이 모양이 있는 줄도 몰랐다 (`_docs/규모_실험.md`).
        "R14",
        "같은 이름의 핀 상수가 서로 다른 핀을 가리킴",
        "차별",
        Severity.CRITICAL,
        ("firmware",),
    ),
    RuleSpec(
        # **우리 보드에서 실제로 난 결함이 만든 규칙이다.** 3.3V MCU 가 5V 릴레이
        # 모듈의 액티브 로우 입력을 몰았고, 끄려고 낸 3.3V 가 하이로 안 읽혀
        # 릴레이가 안 꺼졌다. R04 와 방향이 반대다 — R04 는 들어오는 쪽(파손),
        # R15 는 나가는 쪽(안 망가지는데 안 돈다). 그 방향이 통째로 없었다.
        "R15",
        "MCU 출력 하이가 상대 부품의 입력 문턱에 못 미침",
        "차별",
        Severity.CRITICAL,
        ("netlist", "firmware"),
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
