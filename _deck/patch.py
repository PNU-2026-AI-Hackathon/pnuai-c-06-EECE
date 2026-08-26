#!/usr/bin/env python3
"""기존 발표자료(창업-06-전전컴)에 「머지 차단」 슬라이드를 덧댄다.

**새로 디자인하지 않는다.** 13번 슬라이드를 복제해 두었으므로, 글자만 바꾸고
설명 상자 자리에 스크린샷을 넣는다. 그래야 앞뒤 슬라이드와 같은 물건으로 보인다.

    python3 patch.py <스크린샷.png>

스크린샷은 PR #57 의 머지 상자여야 한다 — 검사 두 개가 `Required` 로 뜨고
「Squash and merge」 버튼이 회색으로 죽어 있는 그 화면.
"""

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

from defusedxml import minidom
from PIL import Image

BASE = Path("base")
SLIDE = BASE / "ppt/slides/slide15.xml"
RELS = BASE / "ppt/slides/_rels/slide15.xml.rels"
MEDIA = BASE / "ppt/media"
EMU = 914400

TITLE_DARK = "빨간불에서 끝나지 않습니다.\n"
TITLE_BLUE = "머지 자체가 막힙니다."

CAPTION = (
    "저희 저장소 main 에 실제로 걸어 둔 규칙입니다 — 회로도 대조 검사가 통과하지 "
    "않으면 버튼이 눌리지 않습니다."
)


def text_of(sp):
    return "".join(t.firstChild.nodeValue for t in sp.getElementsByTagName("a:t") if t.firstChild)


def _zip() -> None:
    out = Path("창업-06-전전컴_최종.pptx")
    if out.exists():
        out.unlink()
    subprocess.run(["zip", "-Xqr", str(Path.cwd() / out), "."], cwd=BASE, check=True)
    with zipfile.ZipFile(out) as z:
        n = len([x for x in z.namelist() if x.startswith("ppt/slides/slide")])
    print(f"  만들어짐: {out}  ({out.stat().st_size} bytes) · 슬라이드 {n}장")


def main():
    # 스크린샷 없이도 돌려서 나머지(제목·캡션·순서·노트)를 먼저 완성해 둔다.
    # **없는 걸 있는 척 그리지 않는다** — 자리는 비워 두고, 그 사실을 화면에 적는다.
    shot = None
    if len(sys.argv) >= 2:
        shot = Path(sys.argv[1])
        if not shot.exists():
            sys.exit(f"파일이 없습니다: {shot}")

    doc = minidom.parse(str(SLIDE))
    tree = doc.getElementsByTagName("p:spTree")[0]
    shapes = [c for c in tree.childNodes if c.nodeType == 1 and c.tagName == "p:sp"]

    # ── 1. 제목 — 두 색 구성을 그대로 쓴다
    title = shapes[0]
    runs = title.getElementsByTagName("a:r")
    assert len(runs) == 2, f"제목 런이 2개가 아니다: {len(runs)}"
    for run, new in zip(runs, (TITLE_DARK, TITLE_BLUE)):
        run.getElementsByTagName("a:t")[0].firstChild.nodeValue = new

    # ── 2. 설명 상자·대본은 걷어낸다. 그 자리에 스크린샷이 들어간다.
    #     페이지 번호와 꼬리말(●–○ Prefab)은 남긴다 — 앞뒤와 이어져야 한다.
    for sp in shapes[1:]:
        txt = text_of(sp)
        if "Prefab" in txt or txt.strip().isdigit():
            if txt.strip() == "13":
                sp.getElementsByTagName("a:t")[0].firstChild.nodeValue = "14"
            continue
        if txt.startswith("이미 저희 저장소에서") and len(txt) < 80:
            # 캡션은 살려서 문구만 바꾼다 — 위치·크기·색이 이미 맞다
            keep = sp.getElementsByTagName("a:t")
            keep[0].firstChild.nodeValue = CAPTION
            for extra in keep[1:]:
                extra.firstChild.nodeValue = ""
            # 캡션을 이미지 아래로 내린다
            off = sp.getElementsByTagName("a:off")[0]
            off.setAttribute("y", str(int(6.28 * EMU)))
            continue
        tree.removeChild(sp)

    # ── 3. 스크린샷을 넣는다. 원본 비율을 지키고 가로 폭에 맞춘다.
    if shot is None:
        SLIDE.write_text(doc.toxml(), encoding="utf-8")
        _zip()
        print("  스크린샷 없이 만들었습니다 — 14번 슬라이드 그림 자리가 비어 있습니다.")
        print("  나중에:  python3 patch.py <스크린샷.png>")
        return

    with Image.open(shot) as im:
        ratio = im.height / im.width
    max_w, max_h = 11.53, 4.55
    w = max_w
    h = w * ratio
    if h > max_h:
        h = max_h
        w = h / ratio
    x = (13.33 - w) / 2
    y = 1.62

    MEDIA.mkdir(parents=True, exist_ok=True)
    dest = MEDIA / "image-15-1.png"
    shutil.copy(shot, dest)

    rels = minidom.parse(str(RELS))
    root = rels.documentElement
    rel = rels.createElement("Relationship")
    rel.setAttribute("Id", "rIdPic1")
    rel.setAttribute(
        "Type",
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image",
    )
    rel.setAttribute("Target", "../media/image-15-1.png")
    root.appendChild(rel)
    RELS.write_text(rels.toxml(), encoding="utf-8")

    pic_xml = f"""<p:pic xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><p:nvPicPr><p:cNvPr id="900" name="MergeBlocked"/><p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr><p:nvPr/></p:nvPicPr><p:blipFill><a:blip r:embed="rIdPic1"/><a:stretch><a:fillRect/></a:stretch></p:blipFill><p:spPr><a:xfrm><a:off x="{int(x*EMU)}" y="{int(y*EMU)}"/><a:ext cx="{int(w*EMU)}" cy="{int(h*EMU)}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:ln w="9525"><a:solidFill><a:srgbClr val="E9EDF3"/></a:solidFill></a:ln></p:spPr></p:pic>"""
    pic = minidom.parseString(pic_xml).documentElement
    # 꼬리말·페이지번호보다 뒤에 두면 그 위를 덮는다. 앞쪽에 넣는다.
    footer = [c for c in tree.childNodes if c.nodeType == 1 and "Prefab" in text_of(c)]
    tree.insertBefore(pic, footer[0]) if footer else tree.appendChild(pic)

    SLIDE.write_text(doc.toxml(), encoding="utf-8")
    _zip()
    print(f"  스크린샷 넣음: {w:.2f}\" x {h:.2f}\"")


if __name__ == "__main__":
    main()
