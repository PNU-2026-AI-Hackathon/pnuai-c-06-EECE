#!/usr/bin/env bash
# 배포한 API 가 진짜로 도는지 60초 안에 확인한다.
#   ./scripts/smoke.sh https://prefab-api-production.up.railway.app
set -euo pipefail

BASE="${1:?사용법: ./scripts/smoke.sh <API_BASE_URL>}"
FIXTURE="$(dirname "$0")/../tests/fixtures/esp32-c6-presence-smart-light.d356"
ORIGIN="${2:-http://localhost:5173}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "1) 헬스체크"
curl -fsS "$BASE/healthz"; echo

echo "2) 규칙 카탈로그"
# f-string 안에 백슬래시를 넣으면 파이썬이 거절한다. 값을 먼저 꺼내 놓는다.
curl -fsS "$BASE/api/v1/rules" | python3 -c 'import json,sys
r = json.load(sys.stdin)["rules"]
done = sum(1 for x in r if x["implemented"])
print(f"  규칙 {len(r)}개 · 구현 {done}개")'

echo "3) CORS 프리플라이트 (이게 막히면 업로드가 통째로 안 된다)"
curl -fsS -o /dev/null -D - -X OPTIONS "$BASE/api/v1/checks" \
  -H "Origin: $ORIGIN" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type" \
  | grep -i "access-control-allow" || { echo "  !! CORS 헤더가 없다"; exit 1; }

echo "4) 실제 보드 업로드"
CHECK_ID=$(curl -fsS -X POST "$BASE/api/v1/checks" -F "netlist=@$FIXTURE" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["check_id"])')
echo "  check_id = $CHECK_ID"

echo "5) 결과가 계약대로 오는지"
# 발견 목록을 여기 적지 않는다. 그러면 tests/ 와 같은 진실을 두 벌 갖게 되고,
# 실제로 한쪽만 갱신돼 낡는다 (CLAUDE.md 10절). 여기서는 계약 불변식만 본다.
# **heredoc 은 stdin 을 차지한다.** 파이프로 준 curl 출력이 파이썬에 안 들어가서
# 이 검사가 한 번도 실제로 돈 적이 없었다. 응답을 파일로 받아 경로로 넘긴다.
curl -fsS "$BASE/api/v1/checks/$CHECK_ID" -o "$TMP/check.json"
python3 - "$TMP/check.json" <<'PYEOF'
import json, sys
r = json.load(open(sys.argv[1], encoding="utf-8"))
s = r["summary"]
assert r["findings"], "  !! 실측 보드에서 발견이 하나도 없다"
assert s["rules_run"] + s["rules_skipped"] == s["rules_total"] > 0, s
assert s["critical"] + s["warning"] + s["cleared"] == len(r["findings"]), s
for f in r["findings"]:
    assert f["rule"] and f["evidence"], f
print(f"  발견 {len(r['findings'])}건 · 규칙 {s['rules_run']}/{s['rules_total']} 실행 · 부품 {s['parts_total']}")
print("  통과")
PYEOF

echo "6) 샘플 검사 — 업로드 없이 결과부터 (F-4)"
# 이 단계가 배포 이미지에 샘플 JSON 이 실렸는지까지 확인한다.
# 안 실리면 조용히 "샘플 없음" 이 되고, 데모 당일에 알게 된다.
SAMPLE=$(curl -fsS "$BASE/" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("sample_check",""))')
if [ -z "$SAMPLE" ]; then
  echo "  !! 루트 응답에 sample_check 가 없다 — 배포 이미지에 샘플 JSON 이 안 실렸다"
  exit 1
fi
echo "  $SAMPLE"
curl -fsS "$BASE$SAMPLE" -o "$TMP/sample.json"
python3 - "$TMP/sample.json" <<'PYEOF'
import json, sys
r = json.load(open(sys.argv[1], encoding="utf-8"))
rules = {f["rule"] for f in r["findings"]}
assert {"R07", "R08"} <= rules, f"  !! 차별 규칙이 샘플에 없다: {rules}"
assert r["inputs"]["firmware"] and r["inputs"]["bom"], r["inputs"]

# **해제가 살아 있는지 본다.** 이 샘플이 파일 없는 방문자의 유일한 입구다.
# 사실 DB 없이 뽑으면 해제가 0건이 되는데, 그러면 첫 화면에서만 차별점이 사라진다.
cleared = [f for f in r["findings"] if f["verdict"] == "PASS"]
assert cleared, "  !! 샘플에 해제된 판정이 없다 — 사실 DB 없이 뽑힌 JSON 이다"
for f in cleared:
    kinds = {e["kind"] for e in f["evidence"]}
    assert "datasheet" in kinds, f"  !! {f['rule']} 해제에 데이터시트 근거가 없다: {kinds}"

print(f"  발견 {len(r['findings'])}건 · 차별 규칙 포함 · 해제 {len(cleared)}건(근거 붙음) · 업로드 0회")
print("  통과")
PYEOF
