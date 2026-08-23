"""저장소가 재시작을 견디는지 **재서** 안다.

환경변수로 "영구임"이라고 적어 두는 방법도 있었다. 그건 **주장이지 사실이 아니다** —
적어 놓고 디스크를 안 붙이면 화면은 안전하다고 말하고 계정은 사라진다.
"""

from __future__ import annotations

from web import storage


def test_처음_뜨면_모른다고_한다(tmp_path):
    """**"안전하다"가 아니다.** 진짜 처음인지 방금 지워진 건지 구분할 수 없다."""
    got = storage.probe(str(tmp_path / "a.db"))
    assert got.state == storage.UNKNOWN
    assert got.survives_restart is False
    assert got.boots == 1


def test_다시_떴는데_표식이_살아_있으면_영구다(tmp_path):
    db = str(tmp_path / "a.db")
    storage.probe(db)
    got = storage.probe(db)
    assert got.state == storage.PERSISTENT
    assert got.survives_restart is True
    assert got.boots == 2


def test_표식이_날아가면_다시_모른다로_돌아간다(tmp_path):
    """재배포로 디스크가 날아간 상황이다. 영구라고 우기지 않는다."""
    db = str(tmp_path / "a.db")
    storage.probe(db)
    storage.probe(db)
    (tmp_path / ("a.db" + storage.MARKER_SUFFIX)).unlink()
    assert storage.probe(db).state == storage.UNKNOWN


def test_처음_본_시각을_이어_간다(tmp_path):
    db = str(tmp_path / "a.db")
    first = storage.probe(db).first_seen
    assert storage.probe(db).first_seen == first


def test_깨진_표식은_없는_것으로_친다(tmp_path):
    """없는 쪽이 안전한 방향이다 — 화면이 경고를 띄운다."""
    db = str(tmp_path / "a.db")
    storage.probe(db)
    (tmp_path / ("a.db" + storage.MARKER_SUFFIX)).write_text("{깨졌다")
    assert storage.probe(db).state == storage.UNKNOWN


def test_표식을_못_써도_서버가_죽지_않는다(tmp_path, monkeypatch):
    """저장소를 못 재는 것 때문에 서버가 안 뜨면 그게 더 큰 문제다."""
    import pathlib

    def refuse(self, *args, **kwargs):
        raise OSError("읽기 전용")

    monkeypatch.setattr(pathlib.Path, "write_text", refuse)
    got = storage.probe(str(tmp_path / "a.db"))
    assert got.state == storage.UNKNOWN


def test_영구에서_모름으로_되돌아가지_않는다(tmp_path):
    """표식이 살아 있는 한, 기동을 반복해도 계속 영구다."""
    db = str(tmp_path / "a.db")
    storage.probe(db)
    states = [storage.probe(db).state for _ in range(5)]
    assert states == [storage.PERSISTENT] * 5
