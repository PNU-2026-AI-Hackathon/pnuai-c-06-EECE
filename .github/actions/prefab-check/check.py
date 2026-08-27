#!/usr/bin/env python3
"""PR 에서 회로도와 코드를 대조한다.

**의존성이 없다.** 러너에 이미 있는 파이썬 표준 라이브러리만 쓴다.
`pip install` 을 넣으면 그것만으로 20초가 늘고, 실패할 자리가 하나 는다.

## 무엇을 하는가

파일을 우리 서버에 올려 검사하고, 결과를 잡 요약에 적고, 기준을 넘으면 빨간불을 켠다.

**파일이 사용자 저장소를 떠난다.** 그 사실을 숨기지 않는다 — 요약 맨 아래에 적는다.
올린 파일은 디스크에 남지 않는다 (`/privacy` 에 적힌 그대로이고 `web/app.py` 가 지킨다).
"""

from __future__ import annotations

import json
import mimetypes
import os
import pathlib
import sys
import urllib.error
import urllib.request
import uuid
import zipfile

#: 화면 주소. 사람이 눌러 볼 수 있는 링크를 만들려면 필요하다.
#: API 와 호스트가 달라서 서버 주소로는 못 만든다.
WEB_BASE = "https://prefab-web.onrender.com"

#: 펌웨어 폴더를 zip 으로 묶을 때 담을 확장자.
#: `runner` 가 읽는 것과 같은 목록이다 — 여기서 더 담아 봐야 서버가 안 본다.
FIRMWARE_SUFFIXES = (".ino", ".cpp", ".c", ".h", ".hpp")

#: 라이브러리·빌드 산출물은 빼고 올린다. 없으면 zip 이 수십 MB 가 된다.
SKIP = ("/lib/", "/libraries/", "/build/", "/.pio/", "/managed_components/",
        "/node_modules/", "/test/", "/tests/", "/examples/", "/.git/")


def fail(message: str) -> None:
    """액션을 세운다. **무엇을 고쳐야 하는지 적는다.**"""
    print(f"::error::{message}")
    sys.exit(1)


def zip_firmware(folder: pathlib.Path) -> bytes:
    """폴더를 메모리에서 zip 으로 묶는다. 임시 파일을 안 만든다."""
    import io

    buf = io.BytesIO()
    n = 0
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(folder.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in FIRMWARE_SUFFIXES:
                continue
            rel = "/" + str(path.relative_to(folder)).lower()
            if any(s in rel for s in SKIP):
                continue
            z.write(path, str(path.relative_to(folder)))
            n += 1
    if n == 0:
        fail(f"{folder} 안에서 펌웨어 소스를 못 찾았습니다 ({', '.join(FIRMWARE_SUFFIXES)}).")
    print(f"펌웨어 {n}개 파일을 묶었습니다.")
    return buf.getvalue()


def build_multipart(parts: list[tuple[str, str, bytes]]) -> tuple[bytes, str]:
    """multipart/form-data 를 손으로 만든다. `requests` 를 안 쓰기 위해서다."""
    boundary = uuid.uuid4().hex
    body = bytearray()
    for field, filename, payload in parts:
        ctype = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        body += f"--{boundary}\r\n".encode()
        body += (
            f'Content-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'
            f"Content-Type: {ctype}\r\n\r\n"
        ).encode()
        body += payload + b"\r\n"
    body += f"--{boundary}--\r\n".encode()
    return bytes(body), f"multipart/form-data; boundary={boundary}"


def call(url: str, key: str, body: bytes | None, ctype: str | None) -> dict:
    req = urllib.request.Request(url, data=body, method="POST" if body else "GET")
    req.add_header("Authorization", f"Bearer {key}")
    if ctype:
        req.add_header("Content-Type", ctype)
    try:
        with urllib.request.urlopen(req, timeout=180) as res:
            return json.loads(res.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        try:
            message = json.loads(detail)["error"]["message"]
        except Exception:
            message = detail[:300]
        # **401 만 우리가 다시 쓴다.** 서버 문구는 브라우저를 쓰는 사람에게
        # 맞춰져 있어서("이메일 하나면 계정을 만들 수 있습니다") CI 에서는
        # 무엇을 고쳐야 할지 안 알려준다. 나머지는 서버 문구를 그대로 쓴다 —
        # 우리가 고쳐 쓰면 원인이 흐려진다.
        if exc.code == 401:
            fail(
                "API 키가 맞지 않습니다. 저장소 Secrets 의 PREFAB_API_KEY 를 확인하세요. "
                "키는 prefab-web.onrender.com 의 「내 검사」 화면에서 만듭니다."
            )
        fail(f"검사에 실패했습니다 (HTTP {exc.code}) — {message}")
    except urllib.error.URLError as exc:
        fail(f"서버에 닿지 못했습니다 — {exc.reason}")
    raise AssertionError("unreachable")


def summarize(result: dict, report_url: str) -> str:
    """잡 요약에 적을 마크다운.

    **못 돌린 규칙을 같이 적는다.** 발견 0건과 「검사가 다 돌았다」는 다르고,
    그 구분이 이 제품의 신뢰다 (헌법 2-4).
    """
    s = result.get("summary") or {}
    crit, warn = s.get("critical", 0), s.get("warning", 0)
    ran, total = s.get("rules_run"), s.get("rules_total")

    head = "회로도와 코드가 어긋난 곳을 찾았습니다" if crit or warn else "어긋난 곳을 찾지 못했습니다"
    lines = [
        f"## Prefab — {head}",
        "",
        f"| 치명 | 경고 | 해제됨 | 실행한 규칙 |",
        f"|---:|---:|---:|---:|",
        f"| {crit} | {warn} | {s.get('cleared', 0)} | "
        f"{ran if ran is not None else '—'} / {total if total is not None else '—'} |",
        "",
    ]

    if ran is not None and total is not None and ran < total:
        lines += [
            f"> **규칙 {total - ran}개는 돌리지 못했습니다.** 발견 {crit + warn}건이 "
            "「이상 없음」을 뜻하지 않습니다. 리포트의 「어디까지 봤나」에서 사유를 확인하세요.",
            "",
        ]

    for f in (result.get("findings") or [])[:10]:
        mark = mark_of(f)
        where = f" · `{f['net']}`" if f.get("net") else ""
        # 제목은 **그 규칙이 무엇을 찾는지**다. 판정이 아니다. 해제된 발견에
        # 제목만 붙이면 초록 체크와 제목이 서로 반대로 읽힌다.
        head = "해제됨 — " if f.get("verdict") == "PASS" else ""
        lines.append(f"- {mark} **{f.get('rule')}** {head}{f.get('title')}{where}")
        for ev in evidence_lines(f):
            lines.append(f"  - {ev}")
    if len(result.get("findings") or []) > 10:
        lines.append(f"- … 그 밖 {len(result['findings']) - 10}건")

    lines += [
        "",
        f"[전체 리포트 보기]({report_url})",
        "",
        "<sub>검사하려고 파일을 Prefab 서버로 보냈습니다. 올린 파일은 디스크에 남기지 않습니다.</sub>",
    ]
    return "\n".join(lines)


def main() -> None:
    key = os.environ.get("PREFAB_API_KEY", "").strip()
    if not key:
        fail("api-key 가 비어 있습니다. 저장소 Secrets 에 PREFAB_API_KEY 를 넣고 넘겨 주세요.")

    netlist = pathlib.Path(os.environ["PREFAB_NETLIST"])
    if not netlist.is_file():
        fail(f"넷리스트를 못 찾았습니다: {netlist}")

    parts = [("netlist", netlist.name, netlist.read_bytes())]

    firmware = (os.environ.get("PREFAB_FIRMWARE") or "").strip()
    if firmware:
        path = pathlib.Path(firmware)
        if not path.exists():
            fail(f"펌웨어를 못 찾았습니다: {path}")
        payload = path.read_bytes() if path.is_file() else zip_firmware(path)
        parts.append(("firmware", "firmware.zip", payload))

    bom = (os.environ.get("PREFAB_BOM") or "").strip()
    if bom:
        path = pathlib.Path(bom)
        if not path.is_file():
            fail(f"부품 목록을 못 찾았습니다: {path}")
        parts.append(("bom", path.name, path.read_bytes()))

    server = os.environ.get("PREFAB_SERVER", "").rstrip("/")
    body, ctype = build_multipart(parts)
    created = call(f"{server}/api/v1/checks", key, body, ctype)

    check_id = created["check_id"]
    report_url = f"{WEB_BASE}/r/{check_id}"
    result = call(f"{server}/api/v1/checks/{check_id}", key, None, None)

    summary = summarize(result, report_url)
    print(summary)

    # **덤이다.** 여기서 무엇이 터져도 검사 결과와 종료 코드는 그대로다.
    post_inline(result, report_url)

    out = os.environ.get("GITHUB_STEP_SUMMARY")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write(summary + "\n")

    s = result.get("summary") or {}
    crit, warn = s.get("critical", 0), s.get("warning", 0)
    if (out := os.environ.get("GITHUB_OUTPUT")):
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"report-url={report_url}\ncritical={crit}\nwarning={warn}\n")

    fail_on = os.environ.get("PREFAB_FAIL_ON", "critical")
    if fail_on == "critical" and crit:
        fail(f"치명 발견 {crit}건 — {report_url}")
    if fail_on == "warning" and (crit or warn):
        fail(f"발견 {crit + warn}건 — {report_url}")

# ------------------------------------------------------ PR 에 줄 단위로 달기
#
# ## 왜 요약만으로 부족한가
#
# 잡 요약은 **Actions 탭에 있다.** 코드를 보는 사람은 diff 화면에 있고, 거기서
# 요약까지 두 번 더 눌러야 한다. 대부분 안 누른다.
#
# 발견에는 이미 `file` · `line` · `snippet` 이 붙어 있다. 그걸 **그 줄 옆에**
# 달면, 고칠 사람이 고칠 자리에서 읽는다.
#
# ## GitHub 의 제약 하나
#
# 리뷰 코멘트는 **diff 에 실린 줄에만** 달린다. 안 바뀐 파일의 줄에 달려고 하면
# 요청 전체가 422 로 죽는다 — 코멘트 하나 때문에 나머지도 다 사라진다.
#
# 그래서 **달 수 있는 줄을 먼저 추려낸다.** 못 다는 것은 조용히 버린다 —
# 요약에는 어차피 다 실려 있다.


def commentable_lines(patch: str | None) -> set[int]:
    """diff 조각에서 **코멘트를 달 수 있는 줄 번호**를 뽑는다.

    `@@ -a,b +c,d @@` 머리를 읽어 새 파일 기준 줄 번호를 센다.
    추가된 줄(`+`)과 그대로인 줄(` `)에만 달 수 있다 — 지워진 줄(`-`)은 없는 줄이다.

    **순수 함수다.**
    """
    if not patch:
        return set()

    lines: set[int] = set()
    cursor = 0
    for raw in patch.split("\n"):
        if raw.startswith("@@"):
            # @@ -12,7 +12,9 @@ ...  →  새 파일이 12번 줄부터
            try:
                cursor = int(raw.split("+", 1)[1].split(",", 1)[0].split(" ", 1)[0])
            except (IndexError, ValueError):
                cursor = 0
            continue
        if cursor == 0:
            continue
        if raw.startswith("-"):
            continue          # 지워진 줄 — 새 파일에는 없다
        if raw.startswith("+") or raw.startswith(" "):
            lines.add(cursor)
            cursor += 1
    return lines


def match_path(evidence_file: str, pr_paths: list[str]) -> str | None:
    """발견이 말하는 파일을 PR 의 실제 경로에 맞춘다.

    발견에는 파일 **이름**만 온다(`main.ino`). PR 은 저장소 기준 **경로**를 쓴다
    (`firmware/main/main.ino`). 뒤에서부터 맞춰 본다.

    **두 개 이상 걸리면 포기한다.** 엉뚱한 파일에 코멘트를 다느니 안 다는 게 낫다.
    """
    name = evidence_file.strip().lstrip("./")
    hits = [p for p in pr_paths if p == name or p.endswith("/" + name)]
    return hits[0] if len(hits) == 1 else None


def mark_of(f: dict) -> str:
    """발견 하나의 기호. **심각도가 아니라 판정으로 정한다.**

    `severity` 는 그 규칙이 어긋났을 때 얼마나 나쁜지를 말할 뿐이다. 규칙이
    보고 나서 **괜찮다고 판정한 것(`PASS`)까지 빨갛게 칠하면** 요약표의 숫자와
    목록의 색이 어긋난다 — 치명 1건인데 빨간 점이 두 개가 된다.
    """
    verdict = f.get("verdict")
    if verdict == "PASS":
        return "✅"
    if verdict == "UNRESOLVED":
        return "⚪"
    return "🔴" if f.get("severity") == "CRITICAL" else "🟠"


def one_line(text: str | None, limit: int = 110) -> str:
    """여러 줄 근거를 목록 한 줄로 눕힌다.

    근거 본문에는 줄바꿈이 들어 있다. 그대로 markdown 목록에 넣으면 둘째 줄부터
    목록 밖으로 튀어나와 **판정과 근거가 따로 노는 것처럼 보인다.**
    """
    flat = " ".join((text or "").split())
    return flat[: limit - 1] + "…" if len(flat) > limit else flat


def evidence_lines(f: dict, limit: int = 3) -> list[str]:
    """근거를 사람이 읽을 한 줄씩으로. 없으면 빈 목록."""
    out: list[str] = []
    for ev in (f.get("evidence") or [])[:limit]:
        kind = ev.get("kind")
        if kind == "firmware" and ev.get("file"):
            line = ev.get("line")
            where = f"`{ev['file']}`" + (f" {line}줄" if isinstance(line, int) else "")
            snip = one_line(ev.get("snippet"), 80)
            out.append(f"코드 {where}" + (f" — `{snip}`" if snip else ""))
        elif kind == "netlist":
            head = one_line(ev.get("text"))
            if head:
                out.append("회로도 — " + head)
        elif kind == "datasheet":
            src = ev.get("source") or ev.get("mpn") or "데이터시트"
            quote = one_line(ev.get("quote"), 80)
            out.append(f"부품 {src}" + (f" — {quote}" if quote else ""))
    return out


def build_comments(findings: list, files: dict) -> list[dict]:
    """리뷰 코멘트 목록. **순수 함수다.**

    `files` 는 `{저장소 경로: 달 수 있는 줄 집합}`.

    한 발견에 근거가 여럿이면 **첫 줄에만 단다.** 같은 발견을 세 줄에 세 번 달면
    diff 가 우리 코멘트로 덮인다 — 그러면 첫 주에 꺼진다.
    """
    made: list[dict] = []
    seen: set[tuple[str, int]] = set()
    done: set[int] = set()

    for i, f in enumerate(findings):
        mark = mark_of(f)
        for ev in f.get("evidence") or []:
            if i in done:
                break
            if ev.get("kind") != "firmware":
                continue
            name, line = ev.get("file"), ev.get("line")
            if not name or not isinstance(line, int):
                continue
            path = match_path(name, list(files))
            if path is None or line not in files[path]:
                continue
            if (path, line) in seen:
                continue
            seen.add((path, line))
            done.add(i)

            body = f"{mark} **{f.get('rule')}** · {f.get('title')}\n\n{f.get('claim') or ''}"
            if f.get("suggestion"):
                body += f"\n\n**다음 단계** — {f['suggestion']}"
            made.append({"path": path, "line": line, "side": "RIGHT", "body": body.strip()})
            break   # 이 발견은 여기까지

    return made


def uncommentable(findings: list, files: dict) -> list[dict]:
    """코멘트를 달 수 없는 발견. `build_comments` 와 같은 기준으로 센다.

    이 PR 에서 바뀌지 않은 줄에는 GitHub 이 코멘트를 못 받는다. 그리고 애초에
    **가리킬 줄이 없는 발견**도 있다 — 「이 핀이 어느 파일에도 안 나온다」 같은
    것이 그렇다. 못 단 것을 말하지 않으면 요약의 발견 수와 화면의 코멘트 수가
    어긋나 보인다 (헌법 2-4).
    """
    got = {c.get("path") for c in build_comments(findings, files)}
    left: list[dict] = []
    for f in findings:
        if mark_of(f) == "✅":
            continue
        hit = False
        for ev in f.get("evidence") or []:
            if ev.get("kind") != "firmware":
                continue
            name, line = ev.get("file"), ev.get("line")
            if not name or not isinstance(line, int):
                continue
            path = match_path(name, list(files))
            if path is not None and line in files[path]:
                hit = True
                break
        if not hit:
            left.append(f)
    return left


def _review_body(summary: dict, comments: list, missed: list, report_url: str) -> str:
    """리뷰 요약 한 덩어리. **못 단 발견을 숨기지 않는다.**"""
    head = (f"**Prefab** — 치명 {summary.get('critical', 0)}"
            f" · 경고 {summary.get('warning', 0)}")
    if not missed:
        mid = f"어긋난 자리에 코멘트를 달았습니다. [전체 리포트]({report_url})"
    else:
        names = " · ".join(f"**{f.get('rule')}**" for f in missed[:4])
        mid = (f"{len(comments)}건을 어긋난 자리에 달았습니다. "
               f"{names} 는 **이 PR 에서 바뀐 줄에 걸리지 않아 달지 못했습니다** — "
               f"[전체 리포트]({report_url}) 에 근거가 다 있습니다.")
    return head + "\n\n" + mid


def _gh(url: str, token: str, data: dict | None = None):
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method="POST" if data else "GET")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "prefab")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as res:
        return json.loads(res.read() or b"{}")


def post_inline(result: dict, report_url: str) -> None:
    """발견을 PR 의 그 코드 줄 옆에 단다.

    **여기서 실패해도 검사는 실패시키지 않는다.** 이건 덤이다 — 요약과 종료 코드가
    본체고, 코멘트를 못 달았다고 빨간불을 켜면 그게 오작동이다.

    토큰이 없거나 PR 이 아니면 조용히 지나간다. 남의 저장소에서 `pull-requests: write`
    권한을 안 줬을 수 있고, 그건 정상이다.
    """
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    event_path = os.environ.get("GITHUB_EVENT_PATH", "")
    if not (token and repo and event_path):
        return

    try:
        with open(event_path, encoding="utf-8") as f:
            number = (json.load(f).get("pull_request") or {}).get("number")
        if not number:
            return

        api = f"https://api.github.com/repos/{repo}/pulls/{number}"
        changed = _gh(f"{api}/files?per_page=100", token)
        files = {
            item["filename"]: commentable_lines(item.get("patch"))
            for item in changed
            if isinstance(item, dict) and item.get("filename")
        }

        findings = result.get("findings") or []
        comments = build_comments(findings, files)
        if not comments:
            return
        missed = uncommentable(findings, files)

        s = result.get("summary") or {}
        _gh(
            f"{api}/reviews",
            token,
            {
                "event": "COMMENT",
                "body": _review_body(s, comments, missed, report_url),
                "comments": comments,
            },
        )
        print(f"PR 에 코멘트 {len(comments)}개를 달았습니다.")
    except Exception as exc:  # noqa: BLE001 — 덤이라서 무엇이 터져도 검사를 막지 않는다
        print(f"::notice::PR 코멘트를 달지 못했습니다 ({exc}). 검사 결과는 위 요약에 있습니다.")

if __name__ == "__main__":
    main()
