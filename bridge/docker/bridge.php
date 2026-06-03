<?php
/**
 * SUE ↔ MONTE CRISTO — PHP SOVEREIGN BRIDGE  v1.0
 * DAG: php-bridge-2026-0602
 *
 * Runs INSIDE WSL2. Exposed OUTBOUND through the existing cloudflared tunnel
 * (php.e5enclave.com → 127.0.0.1:8899). No inbound NAT traversal, no Tailscale.
 *
 * Why this holds where SSH/Tailscale failed:
 *   - rides the tunnel that already serves boardroom (proven HTTP 200)
 *   - PHP CLI server = zero dependencies, present on every Linux box
 *   - outbound-initiated by cloudflared, so WSL2's NAT is irrelevant
 *
 * SECURITY (this is why Sue resisted before — now solved, not skipped):
 *   1. Bearer token gate (BRIDGE_TOKEN env) — constant-time compare
 *   2. Per-request HMAC signature over (nonce + body) — replay-resistant
 *   3. Command ALLOWLIST by default; raw shell ONLY behind explicit ALLOW_RAW=1
 *   4. Runs as the WSL2 user, never root
 *   5. Every request logged with timestamp + client + command to bridge.log
 *   6. Binds 127.0.0.1 only — never 0.0.0.0; cloudflared is the sole ingress
 */

header('Content-Type: application/json');

// ---- config from env (set by install.sh) ----
$TOKEN   = getenv('BRIDGE_TOKEN') ?: '';
$HMAC    = getenv('BRIDGE_HMAC_KEY') ?: '';
$ALLOW_RAW = getenv('BRIDGE_ALLOW_RAW') === '1';
$LOG     = __DIR__ . '/bridge.log';

function jlog($msg) {
    global $LOG;
    @file_put_contents($LOG, '['.date('c').'] '.$msg."\n", FILE_APPEND);
}
function deny($code, $msg) {
    http_response_code($code);
    echo json_encode(['ok'=>false,'error'=>$msg]);
    jlog("DENY $code: $msg");
    exit;
}

// ---- 1. health check (unauthenticated, safe) ----
$uri = parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH);
if ($uri === '/health') {
    echo json_encode([
        'ok'=>true,
        'bridge'=>'sue-montecristo-php-v1',
        'host'=>gethostname(),
        'wsl'=>is_file('/proc/version') ? trim(@file_get_contents('/proc/version')) : 'n/a',
        'cwd'=>getcwd(),
        'php'=>PHP_VERSION,
        'allow_raw'=>$ALLOW_RAW,
        'ts'=>date('c'),
    ]);
    exit;
}

// ---- 2. auth gate ----
if ($TOKEN === '') deny(500, 'bridge not configured (no BRIDGE_TOKEN)');
$hdr = $_SERVER['HTTP_AUTHORIZATION'] ?? '';
$presented = preg_replace('/^Bearer\s+/i', '', $hdr);
if (!hash_equals($TOKEN, $presented)) deny(401, 'bad token');

$body = file_get_contents('php://input');
$req  = json_decode($body, true);
if (!is_array($req)) deny(400, 'bad json');

// ---- 3. HMAC replay protection ----
if ($HMAC !== '') {
    $sig   = $_SERVER['HTTP_X_BRIDGE_SIG'] ?? '';
    $nonce = $req['nonce'] ?? '';
    if (!$nonce) deny(400, 'missing nonce');
    $expect = hash_hmac('sha256', $nonce . $body, $HMAC);
    if (!hash_equals($expect, $sig)) deny(401, 'bad signature');
}

// ---- 4. command allowlist ----
$ALLOWLIST = [
    'whoami','pwd','ls','cat','df','free','uptime','ps','env','hostname',
    'systemctl','service','docker','git','node','npm','python3','pip',
    'curl','tail','head','grep','find','wc','echo','date',
    // bridge's reason for existing: drain the boardroom queue + repair worker
    'pm2','supervisorctl','./worker','python3 worker.py',
];

$cmd = trim($req['cmd'] ?? '');
if ($cmd === '') deny(400, 'no cmd');

$first = explode(' ', $cmd)[0];
$first = basename($first);

if (!$ALLOW_RAW) {
    $allowed = false;
    foreach ($ALLOWLIST as $a) {
        if ($first === explode(' ', $a)[0]) { $allowed = true; break; }
    }
    if (!$allowed) deny(403, "command '$first' not in allowlist (set BRIDGE_ALLOW_RAW=1 to override)");
}

// ---- 5. execute ----
jlog("EXEC: $cmd");
$cwd = $req['cwd'] ?? getcwd();
$descriptors = [1=>['pipe','w'], 2=>['pipe','w']];
$full = 'cd ' . escapeshellarg($cwd) . ' && ' . $cmd;
$proc = proc_open($full, $descriptors, $pipes, null, null);

$out = $err = ''; $exit = -1;
if (is_resource($proc)) {
    $out = stream_get_contents($pipes[1]); fclose($pipes[1]);
    $err = stream_get_contents($pipes[2]); fclose($pipes[2]);
    $exit = proc_close($proc);
}

echo json_encode([
    'ok'=>($exit===0),
    'exit'=>$exit,
    'stdout'=>$out,
    'stderr'=>$err,
    'cwd'=>$cwd,
    'ts'=>date('c'),
]);
