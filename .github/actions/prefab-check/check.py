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
        mark = "🔴" if f.get("severity") == "CRITICAL" else "🟠"
        where = f" · `{f['net']}`" if f.get("net") else ""
        lines.append(f"- {mark} **{f.get('rule')}** {f.get('title')}{where}")
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


if __name__ == "__main__":
    main()
