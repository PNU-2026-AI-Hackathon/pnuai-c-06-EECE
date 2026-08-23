"""검사 중에는 밖으로 나가지 않는다.

요금 안내 화면이 **"검사를 처리하는 동안 AI 호출 0번"**이라고 말한다. 그게
이 사업 모델의 전부다 — 검사가 늘어도 원가가 안 는다는 주장의 근거다.

말로 적어 두면 언젠가 규칙 하나가 조용히 네트워크를 쓰고, 화면의 문장은
거짓이 된 채로 남는다. **그래서 소켓을 막고 검사를 통째로 돌린다.**
"""

from __future__ import annotations

import socket
from pathlib import Path

import pytest

BOARD = Path(__file__).parent.parent / "board" / "board.net.xml"
FIXTURE = Path(__file__).parent / "fixtures" / "esp32-c6-presence-smart-light.d356"


class NetworkUsed(AssertionError):
    """검사 도중 소켓을 열려고 했다."""


@pytest.fixture()
def no_network(monkeypatch):
    """소켓 생성 자체를 막는다. SQLite 는 파일이라 영향을 받지 않는다."""

    def blocked(*args, **kwargs):
        raise NetworkUsed("검사 도중 네트워크를 열려고 했습니다")

    monkeypatch.setattr(socket, "socket", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    return blocked


def _run(fact_store=None):
    from web import service

    return service.run_check(
        netlist_bytes=BOARD.read_bytes(),
        netlist_filename="board.net.xml",
        fact_store=fact_store,
    )


def test_검사는_네트워크_없이_끝난다(no_network):
    result = _run()
    assert result["status"] == "done"
    assert result["findings"], "규칙이 하나도 안 돌았으면 이 테스트는 아무것도 안 지킨다"


def test_사실_DB_를_붙여도_네트워크를_안_쓴다(no_network, tmp_path):
    """데이터시트 해제 경로가 붙은 상태에서도 그렇다.

    **여기가 진짜 위험한 자리다.** "사실이 없으면 그때 데이터시트를 읽어 오자"는
    생각은 자연스럽고, 한 줄이면 되고, 넣는 순간 검사당 원가가 생긴다.
    """
    from prefab.datasheet.store import FactStore

    store = FactStore(str(tmp_path / "facts.db"))
    from web import service

    service.seed_facts("parts", store)
    result = _run(fact_store=store)
    assert result["status"] == "done"
    assert result["summary"]["cleared"] >= 0


def test_IPC_넷리스트로도_마찬가지다(no_network):
    from web import service

    result = service.run_check(
        netlist_bytes=FIXTURE.read_bytes(), netlist_filename="board.d356"
    )
    assert result["status"] == "done"


def test_이_테스트가_실제로_막고_있는지_확인한다(no_network):
    """**막는 시늉만 하는 테스트가 제일 나쁘다.**

    monkeypatch 대상이 틀렸는데 검사가 통과하면, 우리는 지키지도 않는 것을
    지키고 있다고 믿게 된다. 그래서 차단이 사는지 여기서 직접 본다.
    """
    with pytest.raises(NetworkUsed):
        socket.socket()
