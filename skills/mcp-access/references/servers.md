# Server recipes and finding server definitions

Where to find server definitions in harness configuration, and concrete
recipes for the servers this setup actually uses: chrome-devtools-mcp
(stdio), JetBrains IDEs and Metals (persistent), plus the official test
server for validating tooling.

## Contents

- [Finding server definitions](#finding-server-definitions)
- [chrome-devtools-mcp](#chrome-devtools-mcp)
- [JetBrains IDEs (IntelliJ IDEA and others)](#jetbrains-ides-intellij-idea-and-others)
- [Metals](#metals)
- [MCP test server](#mcp-test-server)
- [Persistent-server patterns](#persistent-server-patterns)

## Finding server definitions

To call a server without native MCP tools you need its command line or URL
from the harness configuration. Look for:

- OpenCode: the `"mcp"` block in `opencode.jsonc`. `"type": "local"` has a
  `command` array (stdio server); `"type": "remote"` has a `url`.
- Claude Code / generic: `.mcp.json` (`mcpServers` with `command`, `args`,
  `env`) or the desktop app config (`claude_desktop_config.json`).
- Codex: `[mcp_servers.<name>]` in `~/.codex/config.toml`.
- Copilot CLI: the MCP config JSON (`mcpServers`).
- Grep hint: search the config for `mcpServers` or `"mcp"`.

A stdio `command` array joins into one shell line for `--cmd`:
`["npx","-y","chrome-devtools-mcp@latest"]` becomes
`--cmd 'npx -y chrome-devtools-mcp@latest'`. Environment variables the
server needs (API keys) are inherited from your shell: set them on the
command (`FOO=bar python3 scripts/mcp_call.py ...`).

## chrome-devtools-mcp

Google's official DevTools MCP server; stdio transport; requires Node LTS
and a Chrome install (Google Chrome or Chrome for Testing).

```bash
npx -y chrome-devtools-mcp@latest            # server command (this IS the server)
```

Useful flags: `--headless`, `--isolated` (throwaway profile),
`--channel canary|dev|beta|stable`, `--browser-url http://127.0.0.1:9222`
(attach to an already-running Chrome started with remote debugging),
`--executablePath`, `--userDataDir`, `--viewport`, `--proxyServer`,
`--logFile`. There is no `--browser` or `--port` flag.

Tier 2: `npx -y @modelcontextprotocol/inspector@2.10.1 --cli npx -y
chrome-devtools-mcp@latest -- --method tools/list`

Tier 3: `python3 scripts/mcp_call.py stdio --cmd 'npx -y
chrome-devtools-mcp@latest' list call take_screenshot '{}'`

Note: each server process owns a browser instance, so batch everything you
need into one invocation (navigate, snapshot, click, screenshot in one
session), otherwise you relaunch Chrome per call.

## JetBrains IDEs (IntelliJ IDEA and others)

The built-in MCP Server plugin ships in IDE 2025.2 and later (enable it in
Settings | Tools | MCP Server). The IDE must be running. State (index,
open files) lives in the IDE, so per-call connections are fine.

Endpoints (host `127.0.0.1`; default port for IntelliJ IDEA is 64342,
other products offset by +20):

| IDE | Port | Streamable HTTP |
|-----|------|-----------------|
| IntelliJ IDEA | 64342 | `http://localhost:64342/stream` |
| CLion | 64362 | `http://localhost:64362/stream` |
| GoLand | 64422 | `http://localhost:64422/stream` |
| PhpStorm | 64442 | `http://localhost:64442/stream` |
| PyCharm | 64462 | `http://localhost:64462/stream` |
| WebStorm | 64542 | `http://localhost:64542/stream` |

The same built-in server also serves SSE at `.../sse` (POST to
`.../message`); use the inspector with `--transport sse` for that
endpoint. Ports are user-configurable; the authorized private server runs
at default port + 100 and requires an `IJ_MCP_AUTH_TOKEN` header (the
token comes from IDE-initiated flows). The global server needs no token.
The IDE's own generated client configs include an
`IJ_MCP_SERVER_PROJECT_PATH` header. Add it with `--header` if the server
asks for it.

Tier 2: `npx -y @modelcontextprotocol/inspector@2.10.1 --cli
http://localhost:64342/stream --transport http --method tools/list`

Tier 3: `python3 scripts/mcp_call.py http http://localhost:64342/stream
list`

SSE endpoint (`/sse`): inspector with `--transport sse`. The old
`@jetbrains/mcp-proxy` npm package is deprecated. Prefer the built-in
server's HTTP endpoint.

## Metals

The Scala language server ships an MCP server (since Metals 1.5.3; the
standalone `metals-mcp` launcher with `--transport stdio` since 1.6.7).
Tools: `compile-file`, `compile-module`, `compile-full`, `test`,
`glob-search`, `typed-glob-search`, `inspect`, `get-docs`, `get-usages`,
`get-source`, `import-build`, `find-dep`, `list-modules`, `format-file`,
`generate-scalafix-rule`, `run-scalafix-rule`, `list-scalafix-rules`.

- Editor mode: `metals.startMcpServer = true`; the endpoint is
  `http://localhost:<port>/mcp` (port written to `.metals/mcp.json`; in
  this setup it is `http://localhost:8083/mcp`).
- Standalone: `cs install metals-mcp`, then
  `metals-mcp --workspace . --transport stdio`.

Caveats: wait for indexing before search tools; call `import-build` after
build changes; search results cap at 100 by default. JVM startup plus
indexing makes cold calls slow. Batch ops and raise `--timeout`:

```bash
python3 scripts/mcp_call.py http http://localhost:8083/mcp --timeout 900 \
  call import-build '{}' call inspect '{"position":"..."}' call get-docs '{}'
```

## MCP test server

The official `@modelcontextprotocol/server-everything` validates any tier
quickly. Its tools take simple arguments and need no credentials: `echo`
takes `{"message": string}` and returns `Echo: <message>`, and `get-sum`
takes `{"a": number, "b": number}` and returns the sum.

```bash
npx -y @modelcontextprotocol/server-everything                       # stdio
PORT=3001 npx -y @modelcontextprotocol/server-everything streamableHttp   # HTTP at http://localhost:3001/mcp
```

## Persistent-server patterns

- **IDE-backed servers** (JetBrains): state lives in the IDE; connect,
  call, disconnect per request is fine.
- **Stateful stdio servers** (browsers, JVM tools like Metals): one server
  process per `mcp_call.py` invocation. Pass every op you need on one
  command line so expensive startup happens once, and raise `--timeout`
  for slow starts.
- Never leave server processes running after your session: the script
  shuts its child down on exit (stdin close, then TERM/KILL to the process
  group).
