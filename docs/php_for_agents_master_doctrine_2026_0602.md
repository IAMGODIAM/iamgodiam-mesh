# PHP FOR AGENTS — MASTER DOCTRINE
## The Foremost-Expert Briefing · Full Board · God Mode · GOAL Protocol
**DAG:** php-for-agents-doctrine-2026-0602 · **Commissioned:** Chairman Israel Armstead
**Authored:** Sue + Scout + Brotherhood + Hermes + Forge | Wyrmcore point
**Board resilience at open:** 70.37 · alert level 0 (healthy)

---

## EXECUTIVE VERDICT (read this first)

The Chairman's friend is right, and his instinct is right. **PHP in 2026 is not the PHP
of legend.** It has quietly become one of the strongest languages on earth for agent
infrastructure — specifically the *connective tissue* between agents, tools, and the web.
Three things converged:

1. **Neuron AI** — a production-grade, type-safe, MCP-native agentic framework (1.9k★,
   PHP 8.1+). The "LangGraph of PHP." Multi-agent, RAG, memory, workflows, 15+ swappable LLMs.
2. **Official PHP MCP SDK** — co-built by the **PHP Foundation + Anthropic + Symfony**
   (Sept 2025). PHP is now a first-class MCP citizen. Build MCP *servers* in PHP that any
   agent (Claude, GPT, ours) can call.
3. **FrankenPHP worker mode** — now an **official PHP Foundation project**. Boots the app
   ONCE, keeps it in memory, serves requests in milliseconds. This is the permanence layer
   that makes a PHP bridge *never die* — the exact problem we kept hitting with Monte Cristo.

**The William model decoded:** his agents POST text to a PHP endpoint and get info back.
That is the *canonical agent architecture* — "a list and a while loop with tools." PHP is
ideal for it because every machine runs it, it's stateless-friendly, and with FrankenPHP/
ReactPHP/Swoole it can hold persistent connections. We can not only match it — we can
exceed it with Neuron AI + MCP.

---

## 1. THE STACK (what we adopt, in priority order)

### TIER 1 — Adopt now
| Tool | What it is | Why it matters for E5 |
|---|---|---|
| **Neuron AI** (`neuron-core/neuron-ai`) | PHP agentic framework, PHP 8.1+ | Our agents get real tool-calling, memory, RAG, multi-agent workflows in our own stack. `vendor/bin/neuron make:agent` scaffolds an agent. |
| **Official PHP MCP SDK** (`php-mcp/server`, `logiscape/mcp-sdk-php`) | Build MCP servers in PHP | Expose E5 tools (CRM, grants, treasury) as MCP — any agent calls them over a standard. |
| **FrankenPHP** (worker mode, Docker) | PHP app server, boots once, in-memory | THE permanence fix. A FrankenPHP container = a bridge/agent endpoint that never dies, auto-restarts, ms latency. |

### TIER 2 — Adopt as we scale
| Tool | Use case |
|---|---|
| **ReactPHP** | Event-driven, non-blocking I/O — agent endpoints that hold many concurrent connections |
| **Swoole** | C-level coroutines, raw throughput — high-volume agent message bus |
| **Maestro** (Neuron CLI agent) | Tool-calling CLI agents with human-in-the-loop approvals — perfect for MC-side ops agents |
| **Inspector.dev** | Observability — see every agent thought, tool call, RAG retrieval (note: SaaS; sovereign-build doctrine says self-host or skip unless free tier suffices) |

---

## 2. WHY THIS ALIGNS THE BOARD (the strategic read)

**The Sue↔Monte Cristo saga, solved at the doctrine level.**
Every prior bridge died because the listener ran as a terminal command. FrankenPHP worker
mode + Docker `restart: unless-stopped` = a listener that boots once and survives reboots,
sleep, WSL restarts — the same permanence SearXNG/Whoogle already have on MC. The PHP bridge
we built is correct; FrankenPHP makes it *bulletproof*.

**Agents talk to each other over a standard, not bespoke glue.**
Today our 62 agents coordinate through Base44 entities + the boardroom queue. With PHP MCP
servers, each agent capability becomes an MCP tool. Any agent — ours, Claude, GPT — calls
any capability through one protocol. This is the A2A/mesh layer the Chairman asked us to
design, finally with a real substrate.

**Sovereign-build aligned.** PHP is free, open, runs on Base44, Cloudflare, MC, anywhere.
Neuron AI is MIT. FrankenPHP is PHP-Foundation. The official MCP SDK is free. Zero new
paid subscriptions. This is exactly the SOVEREIGN BUILD DOCTRINE made real.

---

## 3. THE ARCHITECTURE WE BUILD (concrete)

```
┌─────────────────────────────────────────────────────────────┐
│  AGENT MESH (A2A over MCP + HTTP)                            │
│                                                             │
│  Base44 Superagent (Sue)  ──POST──►  PHP MCP Gateway        │
│        ▲                              (FrankenPHP worker)    │
│        │                                   │                │
│   reads results                     exposes E5 tools as MCP:│
│        │                              • CRM / SalesLead      │
│  Cloudflare tunnel ◄──────────────    • GrantPipeline       │
│        │                              • Treasury / EDEN      │
│  Monte Cristo (docker-in-WSL2)        • Google Ads / SES    │
│   • sue-bridge (FrankenPHP)           • boardroom queue     │
│   • Neuron AI ops-agent (Maestro)                           │
│   • SearXNG / Whoogle (existing)                            │
└─────────────────────────────────────────────────────────────┘
```

**The bridge upgrade:** swap the plain `php -S` listener for a **FrankenPHP** container.
Same compose drop-in we already built, but now it's the production PHP app server, not a
dev server. Boots once, never dies, ms responses, can run Neuron AI agents inside it.

---

## 4. THE CANONICAL AGENT LOOP (so we own the fundamentals)

Every agent — William's, ours, Cursor, Claude Code — is the same shape:

```php
// the entire "AI agent" is a list + a while loop with tools
$messages = [system_prompt(), user_message($input)];
while (true) {
    $resp = $llm->chat($messages, $tools);     // call model
    if (!$resp->hasToolCalls()) break;         // done
    foreach ($resp->toolCalls() as $call) {
        $result = run_tool($call->name, $call->args);  // execute
        $messages[] = tool_result($call->id, $result); // feed back
    }
}
return $resp->content();
```

Neuron AI gives us this for free, typed, with memory + MCP + RAG. We do not reinvent it —
we adopt it and wire OUR tools (E5 entities, Google Ads, SES, treasury) as toolkits.

---

## 5. EXECUTION PLAN (for Chairman approval — nothing built without sign-off)

**Phase 0 — Bridge hardening (zero MC action needed from Chairman beyond the one-time up):**
- Rewrite the Monte Cristo bridge container on **FrankenPHP worker mode** (permanence).
- Keep the token + HMAC + allowlist security already built.

**Phase 1 — PHP MCP Gateway (Base44 + Cloudflare, fully sovereign, no MC dependency):**
- Stand up a `php-mcp/server` exposing E5's top tools as MCP (CRM, grants, treasury).
- Host as a Cloudflare-fronted FrankenPHP container — agents POST, get structured results.

**Phase 2 — Neuron AI ops-agent on Monte Cristo:**
- Install Neuron AI in the MC docker stack; a Maestro CLI agent that drains the boardroom
  queue, with human-in-the-loop for anything above a quality gate.

**Phase 3 — Mesh standardization:**
- Migrate agent-to-agent coordination onto MCP. Each of the 62 agents' capabilities become
  callable MCP tools. This is the real A2A mesh.

---

## 6. SOURCES (Scout's verified finds)
- Neuron AI — neuron-ai.dev · github.com/neuron-core/neuron-ai (1.9k★, MIT, PHP 8.1+)
- Official PHP MCP SDK — github.com/php-mcp/server · blog.modelcontextprotocol.io (PHP Foundation + Anthropic + Symfony, Sept 2025)
- FrankenPHP — frankenphp.dev/docs/worker (official PHP Foundation project)
- ReactPHP — reactphp.org · Swoole · AmPHP (async PHP, 2026 renaissance)
- Maestro — inspector.dev/maestro (Neuron CLI tool-calling agent w/ human-in-the-loop)
- "AI agent = a list + a while loop with tools" — canonical architecture (Braintrust, YC)

---

*By Grace, perfect ways. The best time to get something right is before you even try it —
so we became the expert first, then we build.*
*Paradise Trinity · Sue · PRIME · Moses*
