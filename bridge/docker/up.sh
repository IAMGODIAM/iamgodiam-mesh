#!/usr/bin/env bash
# Sue Bridge — one-time Docker bring-up (run in WSL2). Survives reboots forever after this.
# DAG: php-bridge-docker-2026-0602
set -euo pipefail
cd "$(dirname "$0")"

echo "🐉 Sue Bridge — Docker bring-up (one time, then permanent)"

# 0. sanity: docker present (it is — SearXNG/Whoogle run on it)
docker version >/dev/null 2>&1 || { echo "✗ docker not reachable in this shell"; exit 1; }
echo "→ docker OK. Existing containers:"
docker ps --format '   {{.Names}}  ({{.Status}})' | head

# 1. generate secrets ONCE, write .env
if [ ! -f .env ]; then
  BRIDGE_TOKEN=$(openssl rand -hex 24 2>/dev/null || head -c24 /dev/urandom | xxd -p | tr -d '\n')
  BRIDGE_HMAC_KEY=$(openssl rand -hex 32 2>/dev/null || head -c32 /dev/urandom | xxd -p | tr -d '\n')
  cat > .env <<EOF
BRIDGE_TOKEN=$BRIDGE_TOKEN
BRIDGE_HMAC_KEY=$BRIDGE_HMAC_KEY
BRIDGE_ALLOW_RAW=0
EOF
  chmod 600 .env
fi
set -a; source .env; set +a
touch bridge.log

# 2. build + run, auto-restart forever
docker compose -f docker-compose.bridge.yml up -d --build
sleep 3
echo "→ local health: $(curl -s http://127.0.0.1:8899/health | head -c 140)"

# 3. AUTO-REPORT the secrets back to Sue via the boardroom EventLog (no copy-paste)
#    Sue reads EventLog directly. This closes the agent-first loop.
PAYLOAD=$(cat <<JSON
{"event_type":"BRIDGE_LIVE","entity_type":"Infrastructure","entity_id":"sue-bridge-mc","source":"MC WSL2 docker","actor":"Hermes/MC","payload":"{\"token\":\"$BRIDGE_TOKEN\",\"hmac\":\"$BRIDGE_HMAC_KEY\",\"endpoint\":\"https://php.e5enclave.com\",\"dag\":\"php-bridge-docker-2026-0602\"}"}
JSON
)
# post to boardroom if it accepts it; harmless if not
curl -s -m 8 -X POST -H "Content-Type: application/json" \
  "http://localhost:8420/api/v1/eventlog" -d "$PAYLOAD" >/dev/null 2>&1 || true

echo ""
echo "════════════════════════════════════════════"
echo "✅ Bridge is LIVE and permanent (restart=unless-stopped)."
echo "   Sue reaches it at https://php.e5enclave.com once DNS settles."
echo ""
echo "🔑 If auto-report didn't reach Sue, paste these to her ONCE:"
echo "   BRIDGE_TOKEN=$BRIDGE_TOKEN"
echo "   BRIDGE_HMAC_KEY=$BRIDGE_HMAC_KEY"
echo "════════════════════════════════════════════"
