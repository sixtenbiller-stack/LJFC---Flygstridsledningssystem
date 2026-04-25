#!/usr/bin/env bash
set -e

BASE=${1:-http://localhost:8001}
echo "=== LJFC COMMAND — Golden Path Test ==="
echo "Backend: $BASE"
echo ""

echo "1. Load scenario"
curl -sf -X POST "$BASE/scenario/load" -H 'Content-Type: application/json' -d '{"scenario_id":"scenario-alpha"}' | python3 -c "import sys,json; print(f'   OK: {json.load(sys.stdin)}')"

echo "2. Play at 8x"
curl -sf -X POST "$BASE/scenario/control" -H 'Content-Type: application/json' -d '{"action":"play","speed":8}' > /dev/null
echo "   OK"

echo "   Waiting 6s for wave 1..."
sleep 6

echo "3. Check state"
curl -sf "$BASE/state" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'   Time={d[\"current_time_s\"]:.0f}s Tracks={len(d[\"tracks\"])} Wave={d[\"wave\"]}')"

echo "4. Check alerts"
curl -sf "$BASE/alerts" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'   {len(d)} scored alerts')"

echo "5. Generate 3 COAs"
curl -sf -X POST "$BASE/agent/coas" -H 'Content-Type: application/json' -d '{}' | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'   {len(d[\"coas\"])} COAs for wave {d[\"wave\"]}')"

echo "6. Explain"
curl -sf -X POST "$BASE/agent/explain" -H 'Content-Type: application/json' -d '{"coa_id":"coa-w1-a"}' | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'   {len(d[\"explanation\"][\"primary_factors\"])} factors')"

echo "7. Simulate"
curl -sf -X POST "$BASE/agent/simulate" -H 'Content-Type: application/json' -d '{"coa_id":"coa-w1-a","seed":42}' | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'   Score={d[\"outcome_score\"]} intercepted={d[\"threats_intercepted\"]} breaches={d[\"zone_breaches\"]}')"

echo "8. Approve wave 1"
curl -sf -X POST "$BASE/decision/approve" -H 'Content-Type: application/json' -d '{"coa_id":"coa-w1-a"}' | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'   {d[\"decision_id\"]} snap={d[\"source_state_id\"]}')"

echo "   Waiting 6s for wave 2..."
sleep 6

echo "9. Check wave 2"
curl -sf "$BASE/state" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'   Time={d[\"current_time_s\"]:.0f}s Tracks={len(d[\"tracks\"])} Wave={d[\"wave\"]}')"

echo "10. Re-plan"
curl -sf -X POST "$BASE/agent/coas" -H 'Content-Type: application/json' -d '{"wave":2}' | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'    {len(d[\"coas\"])} COAs for wave {d[\"wave\"]}')"

echo "11. Approve wave 2"
curl -sf -X POST "$BASE/decision/approve" -H 'Content-Type: application/json' -d '{"coa_id":"coa-w2-a"}' | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'    {d[\"decision_id\"]} snap={d[\"source_state_id\"]}')"

echo "12. Verify audit log"
curl -sf "$BASE/decisions" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'    {len(d)} records')"

echo ""
echo "=== ALL 12 GOLDEN PATH STEPS PASS ==="
