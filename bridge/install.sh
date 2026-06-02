#!/usr/bin/env bash
# SUE ↔ MONTE CRISTO PHP BRIDGE — one-shot installer  ·  run INSIDE WSL2
# DAG: php-bridge-2026-0602
set -euo pipefail

echo "🐉 Installing Sue↔MonteCristo PHP bridge..."

BRIDGE_DIR="$HOME/.sue-bridge"
mkdir -p "$BRIDGE_DIR"
cd "$BRIDGE_DIR"

# 1. ensure PHP present
if ! command -v php >/dev/null 2>&1; then
  echo "→ PHP not found, installing (sudo)…"
  sudo apt-get update -qq && sudo apt-get install -y php-cli
fi
echo "→ PHP: $(php -v | head -1)"

# 2. fetch the bridge file (pulled from this repo / pasted)
#    install.sh expects bridge.php alongside it
if [ ! -f bridge.php ]; then
  echo "✗ bridge.php must sit next to install.sh. Copy both into $BRIDGE_DIR"; exit 1
fi

# 3. generate secrets (printed ONCE — give these to Sue)
BRIDGE_TOKEN=$(openssl rand -hex 24)
BRIDGE_HMAC_KEY=$(openssl rand -hex 32)
cat > .env <<EOF
BRIDGE_TOKEN=$BRIDGE_TOKEN
BRIDGE_HMAC_KEY=$BRIDGE_HMAC_KEY
BRIDGE_ALLOW_RAW=0
EOF
chmod 600 .env

# 4. start script (persistent, survives logout via nohup/systemd-run if available)
cat > start.sh <<'START'
#!/usr/bin/env bash
cd "$HOME/.sue-bridge"
set -a; source .env; set +a
exec php -S 127.0.0.1:8899 bridge.php >> bridge.log 2>&1
START
chmod +x start.sh

# prefer systemd (WSL2 with systemd=true), else nohup
if pidof systemd >/dev/null 2>&1; then
  mkdir -p "$HOME/.config/systemd/user"
  cat > "$HOME/.config/systemd/user/sue-bridge.service" <<UNIT
[Unit]
Description=Sue Monte Cristo PHP Bridge
[Service]
ExecStart=$BRIDGE_DIR/start.sh
Restart=always
[Install]
WantedBy=default.target
UNIT
  systemctl --user daemon-reload
  systemctl --user enable --now sue-bridge.service
  echo "→ started via systemd (--user), auto-restarts"
else
  pkill -f "php -S 127.0.0.1:8899" 2>/dev/null || true
  nohup ./start.sh >/dev/null 2>&1 &
  echo "→ started via nohup (pid $!)"
fi

sleep 1
echo "→ local health: $(curl -s http://127.0.0.1:8899/health | head -c 120)"

# 5. cloudflared ingress — add php.e5enclave.com → 127.0.0.1:8899
CFG="/etc/cloudflared/config.yml"
[ -f "$CFG" ] || CFG="$HOME/.cloudflared/config.yml"
echo ""
echo "════════════════════════════════════════════════════"
echo "  ADD THIS to cloudflared ingress ($CFG), above the 404 catch-all:"
echo ""
echo "    - hostname: php.e5enclave.com"
echo "      service: http://127.0.0.1:8899"
echo ""
echo "  then:  sudo systemctl restart cloudflared   (or restart the tunnel)"
echo "════════════════════════════════════════════════════"
echo ""
echo "🔑 GIVE THESE TWO VALUES TO SUE (she stores them as secrets):"
echo "    MC_BRIDGE_TOKEN=$BRIDGE_TOKEN"
echo "    MC_BRIDGE_HMAC_KEY=$BRIDGE_HMAC_KEY"
echo ""
echo "✅ Bridge installed. Once the DNS route is live, Sue reaches Monte Cristo directly."
