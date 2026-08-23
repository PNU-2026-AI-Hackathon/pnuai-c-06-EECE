"""홀드아웃 측정 — **한 번도 안 돌려본 남의 보드**에 엔진을 돌린다.

왜 필요한가. 실보드 오탐을 45 → 5 → 2 로 줄였는데 **그 숫자를 같은 보드 6개에서 쟀다.**
그 보드에 맞춰 고쳤으니 과적합일 수 있다. 처음 보는 보드에서 다시 재야 진짜다.

**보드 파일은 저장소에 넣지 않는다** (HANDOFF 6-8). 임시 폴더에 받아서 돌리고,
남는 것은 이 스크립트와 결과 JSON 뿐이다.

    python scripts/holdout.py --out /tmp/holdout            # 받아서 돌린다
    python scripts/holdout.py --out /tmp/holdout --skip-clone   # 이미 받은 것만

정답 라벨이 없다. 그래서 **재현율은 못 잰다** — 여기서 나오는 발견은 전부
"오탐 후보"이고, 사람이 하나씩 보고 판정해야 한다. 그 판정을 `verdicts.json` 에
적으면 다음 실행부터 오탐율이 나온다.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from prefab.netlist.detect import parse_any  # noqa: E402
from prefab.runner import analyze  # noqa: E402

#: 허용 라이선스에 회로도와 펌웨어가 같이 있는 저장소.
#: **이미 측정에 쓴 보드는 뺐다** — 홀드아웃의 뜻이 그거다.
REPOS: tuple[str, ...] = (
    "cikeyz/bahayshield-ultra",
    "emertcakir/OpenAirScope",
    "atoomnetmarc/IoT12",
    "josuegaleas/JayK",
    "goat-hill/bitclock",
    "MakersAsylumIndia/M19O2",
    "StarGate01/hl-alyx-glove",
    "urish/ctf-shittyaddon",
    "gutierrezps/da-pimp-plus",
    "designer2k2/2d-xmas-tree",
    "dilshan/12v-automatic-ups",
    "VorosEgyes/ArcDice",
    "nitefood/opsum",
    "aderusha/HASwitchPlate",
    "bertrandmartel/metec-braille-driver",
    "erikvanzijst/handheld",
    "jsanpe/c2c-64",
    "Allorx/PCB-Design",
    "thejamesrhodes/Hyades-Flight-Computer",
    "brenocq/bldc-motor",
)

FIRMWARE_SUFFIXES = (".ino", ".cpp", ".c", ".h", ".hpp")

#: 펌웨어로 읽을 글자 상한.
#:
#: 저장소 하나가 펌웨어만 630만 자였다. 엔진은 그걸 다 읽어도 되지만
#: **LLM 베이스라인과 같은 입력을 줘야 비교가 성립한다.** 그래서 양쪽에 같은 상한을 건다.
#: 넘으면 조용히 자르지 않고 **무엇을 뺐는지 같이 돌려준다** (헌법 2-4).
FIRMWARE_CHAR_BUDGET = 120_000

#: 회로도 하나가 이보다 적은 넷을 내면 하위 시트만 뽑힌 것이다. 통째로 버린다.
MIN_NETS = 8


def clone(repo: str, into: Path) -> Path | None:
    dest = into / repo.split("/")[-1]
    if dest.exists():
        return dest
    ok = subprocess.run(
        ["git", "clone", "--depth", "1", "-q", f"https://github.com/{repo}.git", str(dest)],
        capture_output=True,
    )
    return dest if ok.returncode == 0 else None


def export_netlists(root: Path, out: Path) -> list[Path]:
    """회로도마다 넷리스트를 뽑는다. 계층 회로도는 **루트 시트**가 전부를 낸다."""
    made: list[Path] = []
    for sch in sorted(root.rglob("*.kicad_sch")):
        target = out / f"{root.name}__{sch.stem}.net.xml"
        done = subprocess.run(
            ["kicad-cli", "sch", "export", "netlist", "--format", "kicadxml",
             "-o", str(target), str(sch)],
            capture_output=True, timeout=180,
        )
        if done.returncode == 0 and target.exists():
            made.append(target)
    return made


def firmware_of(root: Path) -> tuple[dict[str, str], list[str]]:
    """펌웨어 소스를 모은다. 라이브러리·빌드 산출물은 뺀다.

    돌려주는 것은 (읽은 것, **못 읽은 것의 이름**) 이다. 상한에 걸려 뺀 파일을
    조용히 넘기면, 모델도 우리도 못 본 파일에 대해 "문제 없음" 처럼 답하게 된다.

    `.ino` 를 먼저 읽는다 — 스케치가 핀을 정하는 자리라서 예산을 거기에 먼저 쓴다.
    """
    skip = ("/lib/", "/libraries/", "/build/", "/.pio/", "/managed_components/",
            "/node_modules/", "/test/", "/tests/", "/examples/")
    files = [
        p for p in sorted(root.rglob("*"))
        if p.is_file() and p.suffix.lower() in FIRMWARE_SUFFIXES
        and not any(s in ("/" + str(p.relative_to(root))).lower() for s in skip)
    ]
    files.sort(key=lambda p: (p.suffix.lower() != ".ino", str(p)))

    out: dict[str, str] = {}
    omitted: list[str] = []
    used = 0
    for path in files:
        rel = str(path.relative_to(root))
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            omitted.append(rel)
            continue
        if used + len(text) > FIRMWARE_CHAR_BUDGET:
            omitted.append(rel)
            continue
        out[rel] = text
        used += len(text)
    return out, omitted


def run_board(net_path: Path, sources: dict[str, str], omitted: list[str]) -> dict:
    text = net_path.read_text(encoding="utf-8", errors="replace")
    netlist = parse_any(text, net_path.name)
    result = analyze(text, filename=net_path.name, firmware_sources=sources or None)
    return {
        "board": net_path.stem,
        "nets": netlist.net_count,
        "parts": netlist.part_count,
        "firmware_files": len(sources),
        "firmware_omitted": omitted,
        "findings": [
            {"rule": f.rule, "net": f.net, "verdict": f.verdict.value, "claim": f.claim}
            for f in result.engine.findings
            if f.verdict.value != "PASS"
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="홀드아웃 보드에 엔진을 돌린다")
    ap.add_argument("--out", required=True, help="작업 폴더 (저장소 밖)")
    ap.add_argument("--skip-clone", action="store_true")
    ap.add_argument("--json", help="결과를 이 파일에 쓴다")
    args = ap.parse_args()

    work = Path(args.out)
    (work / "nets").mkdir(parents=True, exist_ok=True)

    boards: list[dict] = []
    for repo in REPOS:
        name = repo.split("/")[-1]
        root = work / name
        if not args.skip_clone:
            root = clone(repo, work) or root
        if not root.exists():
            print(f"?? {name:28} 받지 못함", file=sys.stderr)
            continue

        sources, omitted = firmware_of(root)
        nets = export_netlists(root, work / "nets")
        if not nets:
            print(f"-- {name:28} 회로도에서 넷리스트를 못 뽑음", file=sys.stderr)
            continue

        # 계층 회로도는 시트마다 파일이 나온다. **가장 큰 것 하나만** 쓴다 —
        # 하위 시트를 따로 세면 같은 보드를 여러 번 센다.
        best, best_result = None, None
        for net_path in nets:
            try:
                got = run_board(net_path, sources, omitted)
            except Exception as exc:
                print(f"?? {net_path.name}: {type(exc).__name__}: {exc}", file=sys.stderr)
                continue
            if best_result is None or got["nets"] > best_result["nets"]:
                best, best_result = net_path, got

        if best_result is None or best_result["nets"] < MIN_NETS:
            print(f"-- {name:28} 넷이 너무 적음 (하위 시트만 뽑힘)", file=sys.stderr)
            continue

        best_result["repo"] = repo
        boards.append(best_result)
        print(f"OK {name:28} 넷 {best_result['nets']:4} · 부품 {best_result['parts']:4} "
              f"· 펌웨어 {best_result['firmware_files']:3} · 발견 {len(best_result['findings'])}")

    total = sum(len(b["findings"]) for b in boards)
    by_rule: dict[str, int] = {}
    for b in boards:
        for f in b["findings"]:
            by_rule[f["rule"]] = by_rule.get(f["rule"], 0) + 1

    print("=" * 66)
    print(f"보드 {len(boards)}개 · 발견 {total}건")
    for rule, n in sorted(by_rule.items(), key=lambda kv: -kv[1]):
        print(f"  {rule}  {n}건")
    print("=" * 66)
    print("정답 라벨이 없다. 이 발견들은 **오탐 후보**이고 사람이 하나씩 봐야 한다.")

    if args.json:
        Path(args.json).write_text(
            json.dumps({"boards": boards, "by_rule": by_rule}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
