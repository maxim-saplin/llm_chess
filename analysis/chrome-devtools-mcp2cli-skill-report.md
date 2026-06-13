# Chrome DevTools MCP2CLI skill review

## Live app
- URL: `http://localhost:8000/docs/index.html`
- Server: `python3 -m http.server 8000 --directory /Users/admin/src/llm_chess`
- PID file: `/tmp/llm_chess_http.pid`
- Log file: `/tmp/llm_chess_http.log`

## Why the browser kept coming back
- The skill is optimized around **preflight**, not long-lived app driving.
- `bash scripts/preflight.sh` starts a session, proves Chrome works, then stops it.
- That is correct for prerequisites, but it forces a fresh browser lifecycle when the task needs multiple validation passes.
- The skill exposes the raw `mcp2cli` surface, so the agent ends up doing extra hops:
  - start session
  - navigate
  - snapshot
  - resolve uid or script assertion
  - click / wait / re-check
  - stop session
- The skill does not make session reuse a first-class pattern, so a named session can be started/stopped repeatedly instead of staying live across related checks.

## What should change in the skill
1. **Add a persistent app-session workflow**
   - one named session per app
   - reuse the same session across multiple checks
   - stop only once at the end

2. **Add selector-first wrappers**
   - CSS selector clicks
   - selector-based fill/wait/assert/get helpers
   - uid fallback only when needed

3. **Keep raw MCP details as fallback, not the default path**
   - raw `mcp2cli` is fine for debugging
   - the common path should be ergonomic and intent-driven

4. **Make command syntax predictable**
   - no selector/uid confusion in the normal flow
   - concise examples for open/click/fill/wait/assert/snapshot

5. **Add session hygiene guidance**
   - check for existing sessions before starting a new one
   - document how to recover from a leftover live session

## Exact verification steps for the skill

### 1) Preflight and app reachability
```bash
bash /Users/admin/src/llm_chess/.agents/skills/chrome-devtools-mcp2cli/scripts/preflight.sh \
  http://localhost:8000/docs/index.html \
  browser-verify
```

Expected:
- prerequisite checks pass
- Chrome DevTools MCP session starts
- navigation to `http://localhost:8000/docs/index.html` succeeds
- snapshot contains `RootWebArea`

### 2) Start a persistent session for the app
```bash
uvx mcp2cli --session-start browserverify \
  --mcp-stdio "npx -y chrome-devtools-mcp@latest --isolated"
```

### 3) Navigate to the app
```bash
uvx mcp2cli --session browserverify navigate-page \
  --url "http://localhost:8000/docs/index.html" \
  --timeout 60000
```

### 4) Verify main leaderboard headers
```bash
uvx mcp2cli --session browserverify evaluate-script \
  --function "() => Array.from(document.querySelectorAll('#leaderboard thead th')).map(th => th.textContent.trim()).filter(Boolean)"
```

Expected evidence:
```json
["#","Player","Elo","Game Duration","Tokens","Cost/Elo"]
```

### 5) Verify popup content after row interaction
```bash
uvx mcp2cli --session browserverify evaluate-script \
  --function "() => { const row = document.querySelector('#leaderboard tbody tr'); if (!row) return false; row.click(); return true; }"
```

Then:
```bash
uvx mcp2cli --session browserverify evaluate-script \
  --function "() => document.getElementById('cost-per-elo')?.innerText || null"
```

Expected evidence:
- popup text contains `Cost/Elo:`

### 6) Stop the session when done
```bash
uvx mcp2cli --session-stop browserverify
```

## Evidence captured during review
- Main leaderboard headers returned by the browser:
  - `[# , Player, Elo, Game Duration, Tokens, Cost/Elo]`
- Popup cost line returned by the browser:
  - `Cost/Elo: $0.00000 ± $0.00000`

## Recommendation
The skill should shift from a raw-tool tutorial to a **selector-first, persistent-session browser wrapper**. That will remove most of the browser churn and reduce the number of hops required for ordinary app verification.
