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
        "펌웨어 정적 분석기 · 모듈 핀아웃 DB 미구현",
    ),
    RuleSpec(
        "R02",
        "회로도가 SPI flash 핀에 연결",
        "기본",
        Severity.CRITICAL,
        ("netlist",),
        "모듈 핀아웃 DB 미구현",
    ),
    RuleSpec(
        "R03",
        "strapping 핀 부팅 상태 오류",
        "기본",
        Severity.WARNING,
        ("netlist",),
        "모듈 핀아웃 DB 미구현",
    ),
    RuleSpec(
        "R04",
        "외부 부품 출력이 GPIO 입력 최대 정격 초과",
        "기본",
        Severity.CRITICAL,
        ("netlist", "bom"),
        "데이터시트 파이프라인 미구현",
    ),
    RuleSpec(
        "R05",
        "이 칩이 지원하지 않는 주변장치 조합",
        "차별",
        Severity.WARNING,
        ("firmware",),
        "펌웨어 정적 분석기 미구현",
    ),
    RuleSpec(
        "R07",
        "코드가 쓰는 핀이 회로도에 미연결",
        "차별",
        Severity.CRITICAL,
        ("netlist", "firmware"),
        "펌웨어 정적 분석기 미구현",
    ),
    RuleSpec(
        "R08",
        "회로도에 연결됐는데 코드가 초기화 안 함",
        "차별",
        Severity.WARNING,
        ("netlist", "firmware"),
        "펌웨어 정적 분석기 미구현",
    ),
    RuleSpec(
        "R09",
        "부팅 시 출력 나오는 핀에 부하 연결",
        "기본",
        Severity.WARNING,
        ("netlist",),
        "모듈 핀아웃 DB 미구현",
    ),
    RuleSpec(
        "R10",
        "회로도 변경 후 코드 미추종 (드리프트)",
        "차별",
        Severity.WARNING,
        ("netlist", "firmware"),
        "펌웨어 정적 분석기 · git 이력 연동 미구현",
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

TOTAL = len(CATALOG)

BY_ID: dict[str, RuleSpec] = {spec.id: spec for spec in CATALOG}
