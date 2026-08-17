#!/usr/bin/env bash
# 배포한 API 가 진짜로 도는지 60초 안에 확인한다.
#   ./scripts/smoke.sh https://prefab-api-production.up.railway.app
set -euo pipefail

BASE="${1:?사용법: ./scripts/smoke.sh <API_BASE_URL>}"
FIXTURE="$(dirname "$0")/../tests/fixtures/esp32-c6-presence-smart-light.d356"
ORIGIN="${2:-http://localhost:5173}"

echo "1) 헬스체크"
curl -fsS "$BASE/healthz"; echo

echo "2) 규칙 카탈로그"
curl -fsS "$BASE/api/v1/rules" | python3 -c 'import json,sys; r=json.load(sys.stdin)["rules"]; print(f"  규칙 {len(r)}개 · 구현 {sum(x[\"implemented\"] for x in r)}개")'

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

echo "5) 결과가 골든과 같은지"
curl -fsS "$BASE/api/v1/checks/$CHECK_ID" | python3 - <<'PY'
import json, sys
r = json.load(sys.stdin)
got = [(f["rule"], f["net"]) for f in r["findings"]]
want = [("R12","PRESENCE_3V3"), ("R12","_IN_ACTIVE_LOW"), ("R11","PRESENCE_3V3")]
assert got == want, f"  !! 결과가 다르다: {got}"
s = r["summary"]
assert s["rules_run"] + s["rules_skipped"] == s["rules_total"]
print(f"  발견 {len(got)}건 · 규칙 {s['rules_run']}/{s['rules_total']} 실행 · 부품 {s['parts_total']}")
print("  통과")
PY
