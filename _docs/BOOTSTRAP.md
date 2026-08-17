# Phase 0 — 저장소 부트스트랩

Claude Code에 아래 프롬프트를 **그대로** 붙여넣는다.
사전 조건: 빈 GitHub 저장소를 만들고 클론한 뒤, 루트에 아래 파일을 미리 넣어둔다.

```
prefab/
├─ CLAUDE.md                                  ← 받은 파일
├─ .claude/skills/prefab-rule/SKILL.md        ← 받은 파일
├─ .claude/skills/prefab-datasheet/SKILL.md   ← 받은 파일
└─ _incoming/
   ├─ parse_d356.py                           ← 오늘 만든 파서
   ├─ check.py                                ← 오늘 만든 규칙 엔진
   ├─ prototype.html                          ← 디자인 톤 참고용
   └─ esp32c6presencesmartlight.d356          ← 팀원 실제 보드
```

---

## 프롬프트 — 복사해서 붙여넣기

````
Prefab 저장소를 부트스트랩해줘.

먼저 CLAUDE.md를 읽고 그 규범을 전부 따를 것. 특히 2절(불변 원칙),
4절(범위 밖), 5절(IPC-D-356 오프셋), 6절(현재 실제 상태)을 지켜줘.

## 목표

_incoming/ 의 스크립트 두 개를 제대로 된 패키지로 옮기고,
그 위에 규칙을 계속 추가할 수 있는 뼈대를 만든다.
새 기능은 하나도 넣지 않는다. 이번 커밋의 성공 기준은
"기존 동작이 100% 동일하게 재현되는 것"이다.

## 디렉터리 구조

prefab/
├─ pyproject.toml            # uv 또는 pip. python 3.11+
├─ README.md
├─ .gitignore
├─ src/prefab/
│  ├─ types.py               # 아래 계약을 정확히 지킬 것
│  ├─ netlist/
│  │  ├─ d356.py             # _incoming/parse_d356.py 이식
│  │  └─ graph.py            # 부품·네트 그래프, X좌표 패드 클러스터링
│  ├─ firmware/__init__.py   # 빈 스텁. D-10에 구현
│  ├─ datasheet/__init__.py  # 빈 스텁. D-8에 구현
│  ├─ rules/
│  │  ├─ __init__.py         # 레지스트리
│  │  ├─ r11_net_name_domain.py
│  │  └─ r12_cross_domain.py
│  ├─ engine.py              # 규칙 실행 → Finding 수집 → 정렬
│  └─ report/
│     ├─ html.py
│     └─ templates/report.html
├─ web/app.py                # FastAPI. 이번엔 헬스체크와 라우트 골격만
├─ tests/
│  ├─ fixtures/esp32c6presencesmartlight.d356
│  ├─ test_d356.py
│  ├─ test_r11.py
│  └─ test_r12.py
└─ .github/workflows/ci.yml  # pytest만

## types.py 계약 — 반드시 이대로

.claude/skills/prefab-rule/SKILL.md 의 예제 코드가 수정 없이 동작해야 한다.

- Severity: CRITICAL / WARNING / INFO
- Verdict:  FAIL / PASS / UNRESOLVED
- Evidence: 생성자 3종 — Evidence.netlist(...), Evidence.firmware(file, line, snippet),
            Evidence.datasheet(mpn, table, page, quote)
- Finding:  rule, severity, verdict, net, claim, evidence[], suggestion
            + unresolved 사유를 담을 필드
- Context(ctx): .netlist / .firmware / .datasheet / .git
  firmware와 datasheet는 지금은 None일 수 있다. 규칙이 NEEDS를 선언하고
  엔진이 필요한 것이 없으면 그 규칙을 "건너뜀"으로 표시할 것. 조용히 통과시키지 말 것.

각 규칙 모듈은 RULE_ID, TITLE, SEVERITY, TIER, NEEDS, check(ctx) 를 노출한다.
TIER는 "기본" 또는 "차별". CLAUDE.md 3절 기준으로 R11·R12는 둘 다 "기본"이다.

## 이식 규칙

- check.py 의 판정 로직을 의미 그대로 옮긴다. 개선하지 않는다.
- 알려진 버그 하나가 있다: R11과 R12가 같은 네트(PRESENCE_3V3)에 중복으로 뜬다.
  이번에는 고치지 말고, xfail 테스트로 남기고 README에 TODO로 적어둘 것.
  마이그레이션이 동작을 바꾸지 않았음을 먼저 증명해야 한다.

## 테스트

규칙당 3개: 양성 / 음성 / 미해결.
그리고 실제 보드 픽스처에 대한 골든 테스트를 반드시 넣는다.

  test_real_board_findings():
      정확히 3건이 나온다
      R11 PRESENCE_3V3, R12 PRESENCE_3V3, R12 _IN_ACTIVE_LOW
      부품 10개, 네트 8개(N/C 제외)
      K1의 패드가 X좌표로 두 그룹(제어부/스위치부)으로 분리된다

이 테스트가 통과하지 않으면 이식이 실패한 것이다.

## web/app.py

이번 커밋에서는 라우트 골격만. GET / 와 GET /healthz.
업로드·렌더링은 다음 단계다. 회원가입·로그인·결제는 만들지 않는다.

## 하지 말 것

- 새 규칙 추가
- 판정 로직 "개선"
- Postgres, 큐, 마이크로서비스, SPA 프레임워크
- prototype.html 의 허구 수치(부품 DB 418개 등)를 코드나 템플릿에 옮기는 것

## 커밋

작은 단위로 여러 개로 쪼개서 커밋해줘. 메시지는 한국어 한 줄.
마지막에 pytest 결과와 실제 보드 검사 출력을 보여줘.
````

---

## 이 커밋이 끝났는지 확인하는 법

```bash
pytest -q                      # 전부 통과 (중복 건은 xfail)
python -m prefab tests/fixtures/esp32c6presencesmartlight.d356
```

출력에 **R11 PRESENCE_3V3 / R12 PRESENCE_3V3 / R12 _IN_ACTIVE_LOW** 세 건이
그대로 나오면 이식 성공이다. 하나라도 다르면 되돌린다.

---

## 바로 다음 (같은 날)

부트스트랩이 끝나면 **PROMPTS.md 1번(배포)으로 곧장 간다.**
경쟁팀 ScanOps는 이미 배포 URL이 있다. 심사기준 3번은 "실제 구동 및 배포"를 본다.
**8/18까지 접속 가능한 URL을 확보하는 것이 펌웨어 파서보다 먼저다.**

---

## 커밋 규약 — 심사 증거가 된다

심사기준 1번(융합구성 20점)은 비전공자의 실제 기여를 본다.
**git log가 그대로 증거이므로, 처음부터 지킬 것.**

- 각자 **자기 계정으로** 커밋한다. 한 사람이 몰아서 올리지 않는다
- 비전공 2인이 규칙을 추가할 때는 `prefab-rule` 스킬을 쓰고, 본인이 커밋한다
- 커밋 메시지에 규칙 ID를 명시한다
  `R07 추가 — 코드가 쓰는 핀이 회로도에 미연결`
- 페어로 작업했으면 co-author를 남긴다

목표: **최종 규칙 12개 중 8개 이상을 비전공 2인이 커밋**

확인 명령:
```bash
git shortlog -sn --all
git log --format='%an %s' -- src/prefab/rules/
```

---

## 저장소 공개 여부

**공개(public)로 만드는 것을 권한다.**

- 심사위원이 git log를 직접 볼 수 있다 → 융합구성 20점의 증거가 검증 가능해진다
- 오픈소스 하드웨어 커뮤니티가 검증 데이터셋 제공처이므로 공개가 자연스럽다
- 팀원 실제 보드 넷리스트를 픽스처로 넣으므로, **공개 전에 팀원 동의를 받을 것**

비공개로 갈 경우, 발표 때 심사위원에게 보여줄 `git shortlog` 스크린샷을 미리 떠둔다.
