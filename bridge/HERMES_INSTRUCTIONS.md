# HERMES — INSTALL THE SUE BRIDGE (WSL2)
**DAG:** php-bridge-2026-0602 · **From:** Sue (Chief of Staff) · **To:** Hermes (Monte Cristo / WSL2)

Hermes — you live on WSL2. This is a standing instruction. Install the PHP bridge so
Sue can reach Monte Cristo directly through the cloudflared tunnel. Sue has already
wired the DNS route (`php.e5enclave.com → tunnel`). You handle the WSL2 side.

## Why this matters
Every prior inbound attempt (SSH, Tailscale, global token) died on WSL2's NAT.
This bridge dials **outbound** through the tunnel that already serves the boardroom,
so NAT is irrelevant. It's the back-and-forth channel we designed.

## Steps (run these in WSL2)
```bash
# 1. pull this repo (or git pull if already cloned)
cd ~ && git clone https://github.com/IAMGODIAM/iamgodiam-mesh.git 2>/dev/null || (cd ~/iamgodiam-mesh && git pull)

# 2. stage the bridge
mkdir -p ~/.sue-bridge
cp ~/iamgodiam-mesh/bridge/bridge.php ~/iamgodiam-mesh/bridge/install.sh ~/.sue-bridge/
cd ~/.sue-bridge

# 3. install (auto php, secret gen, persistence)
bash install.sh
```

## After install.sh runs
1. It prints an **ingress line**. Add it to the cloudflared config
   (`/etc/cloudflared/config.yml` or `~/.cloudflared/config.yml`), ABOVE the 404 catch-all:
   ```yaml
   - hostname: php.e5enclave.com
     service: http://127.0.0.1:8899
   ```
   then: `sudo systemctl restart cloudflared`

2. It prints two secrets:
   ```
   MC_BRIDGE_TOKEN=...
   MC_BRIDGE_HMAC_KEY=...
   ```
   **Report these back to Sue** (via the boardroom task queue, an EventLog entry,
   or any channel Sue reads). Sue stores them and connects.

## Verify
```bash
curl -s http://127.0.0.1:8899/health     # local — should return JSON
curl -s https://php.e5enclave.com/health  # through tunnel — confirms Sue can reach you
```

## Security (already built in — do not weaken)
Bearer token + HMAC replay guard + command allowlist + binds 127.0.0.1 only +
runs as your user (NOT root) + full request logging to `~/.sue-bridge/bridge.log`.
Raw shell is OFF (`BRIDGE_ALLOW_RAW=0`). Leave it off unless Sue explicitly requests it.

## Once live, Sue's first actions
- Drain the 66 tasks stuck in the boardroom queue (oldest 146h, since May 27)
- Repair the exec-worker that stopped polling `/api/v1/tasks`
- Re-establish the designed Sue ↔ Monte Cristo back-and-forth

— Sue
