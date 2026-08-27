"""GitHub 액션이 PR 에 적는 요약.

**이 문구가 이 제품의 신뢰가 걸린 자리다.** CI 에서는 아무도 리포트를 안 열고
요약 한 줄만 본다. 그 줄이 「발견 0건」만 말하고 못 돌린 규칙을 안 말하면,
사용자는 다 검사해서 깨끗한 줄 읽는다 (헌법 2-4).
"""

from __future__ import annotations

import importlib.util
import pathlib

import pytest

ACTION = pathlib.Path(__file__).resolve().parents[3] / ".github/actions/prefab-check/check.py"


@pytest.fixture(scope="module")
def check():
    spec = importlib.util.spec_from_file_location("prefab_action_check", ACTION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


URL = "https://prefab-web.onrender.com/r/chk_x"


def test_못_돌린_규칙이_있으면_0건이_이상_없음이_아니라고_말한다(check):
    out = check.summarize(
        {"summary": {"critical": 0, "warning": 0, "cleared": 0, "rules_run": 9, "rules_total": 15},
         "findings": []},
        URL,
    )
    assert "6개는 돌리지 못했습니다" in out
    assert "「이상 없음」을 뜻하지 않습니다" in out


def test_다_돌았으면_그_경고를_안_붙인다(check):
    out = check.summarize(
        {"summary": {"critical": 0, "warning": 0, "cleared": 0, "rules_run": 15, "rules_total": 15},
         "findings": []},
        URL,
    )
    assert "돌리지 못했습니다" not in out


def test_규칙_수를_모르면_지어내지_않는다(check):
    """서버가 안 주면 `—` 로 둔다. 화면 규칙과 같다 (웹 헌법 2-1)."""
    out = check.summarize({"summary": {"critical": 1, "warning": 0}, "findings": []}, URL)
    assert "—" in out
    assert "돌리지 못했습니다" not in out


def test_발견을_열_건까지만_적고_나머지_수를_말한다(check):
    findings = [
        {"rule": f"R{i:02d}", "title": "무언가", "severity": "WARNING"} for i in range(14)
    ]
    out = check.summarize({"summary": {"critical": 0, "warning": 14}, "findings": findings}, URL)
    assert "그 밖 4건" in out


def test_파일을_보냈다는_사실을_적는다(check):
    """**숨기지 않는다.** CI 에 넣는 사람은 회사 회로도를 올리는 것이다."""
    out = check.summarize({"summary": {}, "findings": []}, URL)
    assert "Prefab 서버로 보냈습니다" in out


def test_리포트_링크가_들어간다(check):
    assert URL in check.summarize({"summary": {}, "findings": []}, URL)


# ── 액션 정의와 README 예시가 어긋나지 않는가 ──────────────

ROOT = pathlib.Path(__file__).resolve().parents[3]
ACTION_YML = ROOT / ".github/actions/prefab-check/action.yml"
README = ROOT / "README.md"


def _yaml():
    return pytest.importorskip("yaml")


def test_README_예시가_액션의_필수_입력을_다_준다():
    """**한쪽만 고치면 남이 복사한 예시가 안 돈다.**

    액션에 필수 입력을 더해 놓고 README 를 안 고치면, 그 예시를 그대로 붙인
    사람은 첫 실행에서 막힌다. 우리는 그 실패를 못 본다.
    """
    import re

    yaml = _yaml()
    action = yaml.safe_load(ACTION_YML.read_text())
    required = {k for k, v in action["inputs"].items() if v.get("required")}

    block = re.search(r"name: 회로도 ↔ 코드 대조.*?```", README.read_text(), re.S)
    assert block, "README 에서 워크플로 예시를 못 찾았습니다"
    workflow = yaml.safe_load(block.group(0).rstrip("`").rstrip())

    step = next(s for s in workflow["jobs"]["prefab"]["steps"] if "prefab-check" in str(s.get("uses", "")))
    assert required <= set(step["with"]), f"예시에 빠진 필수 입력: {required - set(step['with'])}"


def test_액션이_가리키는_스크립트가_있다():
    yaml = _yaml()
    action = yaml.safe_load(ACTION_YML.read_text())
    run = action["runs"]["steps"][0]["run"]
    assert "check.py" in run
    assert (ACTION_YML.parent / "check.py").is_file()


def test_액션이_넘기는_환경변수와_스크립트가_읽는_것이_같다(check):
    """**환경변수 이름이 어긋나면 조용히 빈 값으로 돈다.** 예외도 안 난다."""
    import re

    yaml = _yaml()
    action = yaml.safe_load(ACTION_YML.read_text())
    passed = set(action["runs"]["steps"][0]["env"])
    read = set(re.findall(r'os\.environ(?:\.get)?\[?\(?"(PREFAB_[A-Z_]+)"', ACTION_YML.parent.joinpath("check.py").read_text()))
    assert read <= passed, f"액션이 안 넘기는 변수를 스크립트가 읽습니다: {read - passed}"


# ── PR 인라인 코멘트 ──────────────────────────────────────────────
#
# GitHub 은 **diff 에 실린 줄에만** 코멘트를 받는다. 안 바뀐 줄에 달려고 하면
# 요청 전체가 422 로 죽어서 **나머지 코멘트까지 다 사라진다.**
# 그래서 달 수 있는 줄을 먼저 추려내는 것이 이 기능의 전부다.


def test_diff_에서_달_수_있는_줄만_고른다(check):
    patch = """@@ -12,4 +12,6 @@ void setup() {
 const int A = 1;
-const int B = 2;
+const int B = 3;
+const int C = 4;
 void loop() {"""
    # 지워진 줄(-)은 새 파일에 없다. 나머지는 12번부터 이어진다
    assert check.commentable_lines(patch) == {12, 13, 14, 15}


def test_조각이_없으면_아무_줄도_못_단다(check):
    """바이너리나 아주 큰 파일은 GitHub 이 patch 를 안 준다."""
    assert check.commentable_lines(None) == set()
    assert check.commentable_lines("") == set()


def test_파일_이름을_저장소_경로에_맞춘다(check):
    """발견에는 이름만 오고(main.ino), PR 은 경로를 쓴다(firmware/main/main.ino)."""
    assert check.match_path(
        "main.ino", ["firmware/main/main.ino", "docs/x.md"]
    ) == "firmware/main/main.ino"


def test_같은_이름이_둘이면_안_단다(check):
    """**엉뚱한 파일에 코멘트를 다느니 안 다는 게 낫다.**"""
    assert check.match_path("main.ino", ["a/main.ino", "b/main.ino"]) is None


def test_diff_밖의_줄에는_안_단다(check):
    """이걸 안 거르면 요청 전체가 422 로 죽고 나머지 코멘트도 같이 사라진다."""
    findings = [{
        "rule": "R07", "title": "코드가 쓰는 핀이 회로도에 미연결", "severity": "CRITICAL",
        "claim": "코드가 D4 를 읽습니다.",
        "evidence": [{"kind": "firmware", "file": "main.ino", "line": 999, "snippet": "x"}],
    }]
    got = check.build_comments(findings, {"firmware/main.ino": {10, 11, 12}})
    assert got == []


def test_한_발견에_코멘트_하나만_단다(check):
    """근거가 세 줄이라고 세 번 달면 diff 가 우리 코멘트로 덮인다."""
    findings = [{
        "rule": "R07", "title": "제목", "severity": "CRITICAL", "claim": "설명",
        "evidence": [
            {"kind": "firmware", "file": "main.ino", "line": 10, "snippet": "a"},
            {"kind": "firmware", "file": "main.ino", "line": 11, "snippet": "b"},
        ],
    }]
    got = check.build_comments(findings, {"firmware/main.ino": {10, 11}})
    assert len(got) == 1
    assert got[0]["line"] == 10


def test_코멘트에_규칙과_다음_단계가_실린다(check):
    findings = [{
        "rule": "R07", "title": "코드가 쓰는 핀이 회로도에 미연결", "severity": "CRITICAL",
        "claim": "코드가 D4(GPIO22)를 입력으로 읽습니다.",
        "suggestion": "D2 로 되돌리거나 회로도에 D4 를 배선하세요.",
        "evidence": [{"kind": "firmware", "file": "main.ino", "line": 15, "snippet": "x"}],
    }]
    body = check.build_comments(findings, {"fw/main.ino": {15}})[0]["body"]
    assert "R07" in body
    assert "D4(GPIO22)" in body
    assert "다음 단계" in body and "되돌리거나" in body


def test_회로도_근거에는_안_단다(check):
    """넷리스트는 PR diff 에 없을 수도 있고, 있어도 줄 번호가 뜻이 다르다."""
    findings = [{
        "rule": "R12", "title": "제목", "severity": "CRITICAL", "claim": "설명",
        "evidence": [{"kind": "netlist", "text": "U1.D2 → NET"}],
    }]
    assert check.build_comments(findings, {"a/b.ino": {1, 2, 3}}) == []


def test_진입점이_파일_맨_끝에_있다():
    """**실제로 밟은 버그다 (8/26).**

    `if __name__ == "__main__": main()` **뒤에** 함수를 덧붙였더니, `main()` 이
    돌 때는 그 함수가 아직 정의되지 않아 러너에서 `NameError` 로 죽었다.

    파이썬은 위에서 아래로 실행한다. 진입점 뒤의 정의는 `main()` 이 끝난 뒤에야
    평가된다. 단위 테스트는 모듈만 import 하므로 이 실수를 못 잡는다 —
    **파일 순서를 직접 본다.**
    """
    text = ACTION.read_text(encoding="utf-8")
    assert text.rstrip().endswith("main()"), "진입점이 파일 맨 끝이 아닙니다"

    entry = text.index('if __name__ == "__main__"')
    after = text[entry:]
    assert "\ndef " not in after, "진입점 뒤에 함수 정의가 있습니다 — 러너에서 NameError 가 납니다"


def test_main_이_부르는_이름이_전부_정의돼_있다():
    """import 만으로는 「정의는 됐지만 순서가 틀린」 경우를 못 본다."""
    import ast

    tree = ast.parse(ACTION.read_text(encoding="utf-8"))
    defined = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
    main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    called = {
        n.func.id
        for n in ast.walk(main)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
    }
    missing = {c for c in called if c.islower() and "_" in c or c in defined} - defined
    assert not missing, f"main 이 부르는데 없는 함수: {missing}"


def test_해제된_발견은_빨간점이_아니다(check):
    """`severity` 는 규칙의 등급이고 `verdict` 가 이번 판정이다.

    규칙이 보고 나서 **괜찮다고 판정한 것(PASS)** 까지 빨갛게 칠하면,
    요약표의 「치명 1」과 목록의 빨간 점 두 개가 어긋난다. 실제로 시연
    저장소에서 그렇게 나왔다.
    """
    mod = check
    assert mod.mark_of({"severity": "CRITICAL", "verdict": "PASS"}) == "✅"
    assert mod.mark_of({"severity": "CRITICAL", "verdict": "FAIL"}) == "🔴"
    assert mod.mark_of({"severity": "WARNING", "verdict": "FAIL"}) == "🟠"
    assert mod.mark_of({"severity": "CRITICAL", "verdict": "UNRESOLVED"}) == "⚪"


def test_빨간점_수가_요약표_치명수와_같다(check):
    mod = check
    result = {
        "summary": {"critical": 1, "warning": 1, "cleared": 1,
                    "rules_run": 15, "rules_total": 15},
        "findings": [
            {"rule": "R07", "title": "가", "severity": "CRITICAL", "verdict": "FAIL"},
            {"rule": "R12", "title": "나", "severity": "CRITICAL", "verdict": "PASS"},
            {"rule": "R08", "title": "다", "severity": "WARNING", "verdict": "FAIL"},
        ],
    }
    out = mod.summarize(result, "https://example.test/r/chk_1")
    assert out.count("🔴") == 1
    assert out.count("✅") == 1


def test_근거의_줄바꿈이_목록을_깨지_않는다(check):
    """근거 본문에는 줄바꿈이 있다. 그대로 넣으면 둘째 줄이 목록 밖으로 튄다."""
    mod = check
    result = {
        "summary": {"critical": 1, "warning": 0, "cleared": 0,
                    "rules_run": 15, "rules_total": 15},
        "findings": [{
            "rule": "R07", "title": "가", "severity": "CRITICAL", "verdict": "FAIL",
            "evidence": [{"kind": "firmware", "file": "a.ino", "line": 15,
                          "snippet": "첫 줄\n둘째 줄\n셋째 줄"}],
        }],
    }
    out = mod.summarize(result, "https://example.test/r/chk_1")
    body = [l for l in out.splitlines() if "둘째 줄" in l]
    assert body and body[0].startswith("  - 코드")
