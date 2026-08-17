"""테스트용 IPC-D-356 레코드 생성기.

실측 오프셋(CLAUDE.md 5절)을 그대로 써서 만든다.
합성 픽스처가 진짜 파일과 같은 자리를 쓰는지 test_d356.py 가 검증한다.
"""

from __future__ import annotations

RECORD_SMT = "327"
RECORD_THRU = "317"


def rec(
    net: str,
    ref: str,
    pin: str = "",
    x: float = 0.0,
    y: float = 0.0,
    record: str = RECORD_SMT,
) -> str:
    """좌표는 inch. 핀 이름은 실제 파일과 똑같이 4자에서 잘린다."""
    line = record + net.ljust(14)[:14] + " " * 3 + ref.ljust(6)[:6] + "-" + pin.ljust(4)[:4]
    line = line.ljust(41)
    line += f"X{'+' if x >= 0 else '-'}{abs(int(round(x * 10000))):06d}"
    line += f"Y{'+' if y >= 0 else '-'}{abs(int(round(y * 10000))):06d}"
    return line


def via(net: str, x: float = 0.0, y: float = 0.0) -> str:
    return rec(net, "VIA", "", x, y, record=RECORD_THRU)


def board(*lines: str) -> str:
    header = "P  CODE 00\nP  UNITS CUST 0\n"
    return header + "\n".join(lines) + "\n999\n"
