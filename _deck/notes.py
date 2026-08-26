#!/usr/bin/env python3
"""발표 노트를 채운다 — 10분에 맞춰서.

기존 자료는 글자만 세면 4분 14초다. 모자란 게 아니라, **이미지만 있는 슬라이드
네 장에 할 말이 안 적혀 있어서** 실제 발표 시간이 사람마다 달라진다.
여기서 슬라이드마다 할 말과 목표 시간을 박아 둔다.

노트 슬라이드는 이미 14장 다 있고 본문만 비어 있다. 새로 만들지 않고 채운다.
"""

import re
import subprocess
import sys
from pathlib import Path

from defusedxml import minidom

BASE = Path("base")
NOTES = BASE / "ppt/notesSlides"

A = "http://schemas.openxmlformats.org/drawingml/2006/main"

#: 슬라이드 번호 → (목표 초, 할 말)
#: 합이 600초를 넘지 않게 짰다. 실제로는 넘기 마련이라 8분 30초에 맞춰 뒀다.
SCRIPT = {
    1: (25, """[표지 · 25초]
안녕하세요. 창업트랙 C-06 팀 전전컴입니다.
저희는 보드를 발주하기 전에, 코드와 회로도가 어긋난 곳을 찾는 도구를 만들었습니다.
한 장면부터 보여드리겠습니다."""),

    2: (40, """[어긋난 코드 · 40초]
공개 저장소에서 저희 도구가 실제로 찾은 것입니다.
납땜을 바꾸면서 백라이트 핀을 19번으로 옮겨 놨는데, 다른 파일의 상수는 25번에 그대로 남아 있습니다.
그리고 25번은 이제 디스플레이 데이터선입니다.
아직 아무도 그 상수를 안 써서 안 터졌을 뿐이고, 같은 파일에 적혀 있는 기능이 켜지는 순간 데이터선에 신호가 걸립니다.
컴파일도 되고 업로드도 됩니다. 어느 검사에도 안 걸립니다."""),

    3: (40, """[비용 · 40초]
소프트웨어는 잘못돼도 다시 배포하면 됩니다. 하드웨어는 돈이 사라집니다.
설계 프로젝트 조사를 보면 평균 2.9회를 다시 만들고, 한 번에 약 6천만원, 8.5일이 듭니다.
저희가 줄이려는 게 이 숫자입니다."""),

    4: (35, """[시장 근거 · 35초]
저희만 그렇게 보는 게 아닙니다. 서울시가 이 문제에 세금을 쓰고 있습니다.
시제품 제작을 지원하는 이유로 "위험부담이 커서 진입장벽이 크다"를 듭니다.
그런데 지원은 만들어 주는 것이지, 틀린 걸 미리 잡아 주지는 않습니다."""),

    5: (30, """[빈자리 · 30초]
지금 도구들이 보는 곳을 그려 봤습니다.
회로도 검사 도구는 회로도만 봅니다. 컴파일러는 코드만 봅니다.
둘 사이는 아무도 안 봅니다. 저희가 들어가려는 자리가 여기입니다."""),

    6: (20, """[한 문장 · 20초]
저희가 하는 일은 한 문장입니다.
이미 짜 놓은 펌웨어가, 바뀐 회로도를 따라가고 있는지 검사합니다."""),

    7: (45, """[발견 카드 · 45초]
2장에서 보신 그 저장소를 그대로 넣은 결과입니다.
판정 하나에 근거가 세 줄 붙습니다. 회로도가 아는 것, 코드가 아는 것, 부품이 아는 것.
코드는 파일 이름과 줄 번호까지 나옵니다.
그리고 맨 아래를 봐 주세요. 부품 정보는 "모름"이라고 적혀 있습니다.
확인 못 한 것을 "이상 없음"이라고 하지 않습니다. 이게 저희가 제일 신경 쓴 부분입니다."""),

    8: (35, """[다른 저장소 · 35초]
다른 저장소에서 찾은 것입니다. 한 핀에 데이터선 두 개가 물려 있습니다.
이건 회로도만 봐도 알 수 있는 종류인데, 사람이 놓친 겁니다.
저희는 이걸 오픈소스 저장소에 이슈로 제보했습니다."""),

    9: (30, """[오탐 0 · 30초]
경고를 많이 내는 건 쉽습니다. 안 내는 게 어렵습니다.
한 번도 안 써 본 보드 38개에 처음 돌렸을 때는 14건이 나왔습니다. 대부분 오탐이었습니다.
원인 세 개를 고쳐서 1건으로 줄였고, 그 하나는 진짜였습니다.
경고를 안 내는 것도 기능입니다."""),

    10: (55, """[LLM 대조 · 55초]
가장 많이 받는 질문입니다. 그냥 AI에 물어보면 안 되냐.
궁금해서 실제로 재봤습니다. 같은 보드 28개를 대형 모델과 나란히 돌렸습니다.
모델은 6개를 통째로 건너뛰었습니다. 입력이 커서요. 안 본 보드는 문제 없는 보드가 아니라 모르는 보드입니다.
경고는 세 배 가까이 많이 냈는데, 그중 10건은 경고 안에 "확인할 수 없다"가 들어 있었습니다.
받아 든 사람이 다시 확인해야 하면 도구가 아니라 숙제입니다.
모델이 저희보다 잘한 것도 있었습니다. 저희가 못 보던 결함을 하나 찾아냈고, 규칙으로 만들어 넣었습니다.
저희가 파는 건 "AI보다 똑똑하다"가 아니라 "같은 파일이면 언제나 같은 답"입니다."""),

    11: (30, """[고객 · 30초]
저희 고객 셋입니다. 하드웨어 스타트업, 대학 연구실, 중소 제조업 R&D팀.
공통점은 회로도를 검토해 줄 사람이 없다는 것입니다.
대기업에는 그 사람이 따로 있습니다. 이 셋에는 없습니다."""),

    12: (40, """[요금 · 40초]
무료로도 검사는 무제한입니다. 판정 원가가 실제로 0에 가깝기 때문입니다 —
판정은 순수한 코드라 AI도 네트워크도 쓰지 않습니다.
돈은 팀으로 쓸 때 받습니다. 재작업 한 번이 수천만원인데 구독료는 그 백분의 일입니다.
한 번만 막아도 몇 년치가 회수됩니다."""),

    13: (35, """[CI · 35초]
지금까지 보여드린 건 파일을 올려 한 번 검사하는 모습입니다.
하지만 회로도는 계속 바뀝니다. 그래서 검사도 계속 돌아야 합니다.
최종 형태는 코드를 고칠 때마다 자동으로 도는 검사입니다.
개발팀이 이미 쓰는 자리에 그대로 들어갑니다."""),

    14: (45, """[머지 차단 · 45초]  ★ 새 슬라이드
그리고 빨간불에서 끝나지 않습니다.
이건 저희 저장소의 실제 화면입니다. 회로도를 예전 상태로 되돌린 PR을 하나 올려 뒀습니다.
회로도 대조 검사가 실패했고, 오른쪽에 Required라고 붙어 있습니다.
아래 머지 버튼을 봐 주세요. 회색입니다. 눌리지 않습니다.
어긋난 회로도는 저장소에 들어갈 수 없습니다.
사람이 검토를 깜빡해도 막힙니다 — 이게 저희가 팀 단위로 파는 이유입니다."""),

    15: (25, """[마무리 · 25초]
보드를 뽑기 전에 아는 것과, 뽑고 나서 아는 것의 차이가 6천만원입니다.
그 차이가 이 두 줄에서 갈립니다.
지금 열려 있습니다. 감사합니다."""),
}


def notes_path_for_position(pos: int) -> Path | None:
    """발표 순서 `pos` 번째 슬라이드의 노트 파일을 찾는다.

    **파일 번호로 찾으면 안 된다.** 슬라이드를 하나 끼워 넣는 순간
    `slide15.xml` 이 14번째 자리에 앉아서 번호와 자리가 어긋난다.
    """
    pres = minidom.parse(str(BASE / "ppt/presentation.xml"))
    rels = minidom.parse(str(BASE / "ppt/_rels/presentation.xml.rels"))
    rid2t = {r.getAttribute("Id"): r.getAttribute("Target")
             for r in rels.getElementsByTagName("Relationship")}
    ids = pres.getElementsByTagName("p:sldId")
    if not 1 <= pos <= len(ids):
        return None
    slide = Path(rid2t[ids[pos - 1].getAttribute("r:id")]).name
    srels = BASE / f"ppt/slides/_rels/{slide}.rels"
    if not srels.exists():
        return None
    doc = minidom.parse(str(srels))
    for r in doc.getElementsByTagName("Relationship"):
        if "notesSlide" in r.getAttribute("Type"):
            return BASE / "ppt/notesSlides" / Path(r.getAttribute("Target")).name
    return None


def set_notes(num: int, text: str) -> bool:
    path = notes_path_for_position(num)
    if path is None:
        return False
    doc = minidom.parse(str(path))
    body = None
    for sp in doc.getElementsByTagName("p:sp"):
        ph = sp.getElementsByTagName("p:ph")
        if ph and ph[0].getAttribute("type") == "body":
            body = sp
            break
    if body is None:
        return False

    tx = body.getElementsByTagName("p:txBody")[0]
    for p in list(tx.getElementsByTagName("a:p")):
        tx.removeChild(p)

    for line in text.split("\n"):
        p = doc.createElementNS(A, "a:p")
        if line.strip():
            r = doc.createElementNS(A, "a:r")
            rPr = doc.createElementNS(A, "a:rPr")
            rPr.setAttribute("lang", "ko-KR")
            rPr.setAttribute("dirty", "0")
            r.appendChild(rPr)
            t = doc.createElementNS(A, "a:t")
            t.appendChild(doc.createTextNode(line))
            r.appendChild(t)
            p.appendChild(r)
        tx.appendChild(p)

    path.write_text(doc.toxml(), encoding="utf-8")
    return True


def main():
    done = []
    missing = []
    for num, (_, text) in SCRIPT.items():
        (done if set_notes(num, text) else missing).append(num)

    total = sum(sec for sec, _ in SCRIPT.values())
    m, s = divmod(total, 60)
    print(f"  노트 기록: {len(done)}장" + (f" · 노트 슬라이드 없음: {missing}" if missing else ""))
    print(f"  목표 합계 {m}분 {s}초 (10분 대비 {600 - total}초 여유)")
    for num, (sec, _) in SCRIPT.items():
        bar = "█" * (sec // 5)
        print(f"    {num:>2}  {sec:>3}초  {bar}")


if __name__ == "__main__":
    main()
