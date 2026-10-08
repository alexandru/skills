# The MCP wire protocol (JSON-RPC) without an SDK

MCP is JSON-RPC 2.0 over one of three transports: stdio (newline-delimited
messages on the server process's stdin/stdout), streamable HTTP (JSON-RPC
POSTed to a single endpoint), and the deprecated HTTP+SSE transport. This
reference teaches the raw protocol so a server can be called with
`scripts/mcp_call.py`, a shell pipeline, or curl. The bundled script
automates everything here; use this page to understand what it does, to
debug with `--verbose`, or to hand-write calls.

## Contents

- [JSON-RPC 2.0 layer](#json-rpc-20-layer)
- [Protocol revisions and negotiation](#protocol-revisions-and-negotiation)
- [The initialize handshake](#the-initialize-handshake)
- [tools/list](#toolslist)
- [tools/call](#toolscall)
- [stdio transport](#stdio-transport)
- [Streamable HTTP with curl](#streamable-http-with-curl)
- [Stateless servers (2026-07-28)](#stateless-servers-2026-07-28)
- [SSE-only servers](#sse-only-servers)
- [Security notes](#security-notes)

## JSON-RPC 2.0 layer

```json
{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{"cursor":"..."}}
{"jsonrpc":"2.0","method":"notifications/initialized"}
{"jsonrpc":"2.0","id":1,"result":{"tools":[...]}}
{"jsonrpc":"2.0","id":1,"error":{"code":-32602,"message":"Unknown tool: x","data":{}}}
```

- Requests carry an `id` (string or integer, never null); notifications
  omit it; responses repeat it and carry exactly one of `result` or
  `error`. Batching (JSON arrays of messages) is not supported in MCP.
- Common error codes: `-32700` parse error, `-32600` invalid request,
  `-32601` method not found, `-32602` invalid params, `-32603` internal
  error, `-32022` unsupported protocol version, `-32020` header mismatch.

## Protocol revisions and negotiation

| Revisions | Behavior |
|-----------|----------|
| `2024-11-05` .. `2025-11-25` | handshake era: `initialize` + `notifications/initialized`; streamable HTTP or SSE |
| `2026-07-28` (current) | stateless: no `initialize`, no sessions, per-request `_meta` |

Handshake-era servers (through `2025-11-25`) answer an `initialize` request
with the same version if they support it, otherwise with another version
they do support. Use the server's returned version in later
`MCP-Protocol-Version` headers. If they reject the proposed version, the
error (`-32022`, or `-32602` from handshake-era servers) carries
`data.supported` listing what they accept.
Stateless-era servers (`2026-07-28`) have no `initialize` at all; see
[Stateless servers](#stateless-servers-2026-07-28). Proposing `2025-06-18`
works with the installed base. `scripts/mcp_call.py` negotiates
automatically: it retries with an advertised version on `-32022`/`-32602`
and switches to stateless mode on `-32601`.

## The initialize handshake

Before any other request, send `initialize`, wait for the response, then
send the `notifications/initialized` notification:

```json
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{
  "protocolVersion":"2025-06-18",
  "capabilities":{},
  "clientInfo":{"name":"my-client","version":"1.0"}}}
```

The response result carries `protocolVersion`, the server's
`capabilities` (e.g. `{"tools":{"listChanged":true}}`), and `serverInfo`.
The client SHOULD NOT send other requests before the initialize response
arrives. The emergency pipeline below bends that rule by waiting blindly;
`scripts/mcp_call.py` waits for the response.

## tools/list

```json
{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}
```

Result: `{"tools":[{"name":"echo","description":"...","inputSchema":{"type":"object","properties":{...},"required":[...]}}],"nextCursor":"..."}`.
If `nextCursor` is present, repeat with `{"cursor":"<nextCursor>"}` and
merge, until it is absent. Read each tool's `inputSchema` before calling:
`required` lists mandatory argument names; `properties` documents types.

## tools/call

```json
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{
  "name":"echo","arguments":{"message":"hello"}}}
```

- `arguments` is optional and is a single JSON object matching `inputSchema`.
- Success result: `{"content":[{"type":"text","text":"..."}],"isError":false}`
  (content items may also be `image`, `audio`, `resource`, `resource_link`;
  `structuredContent` may carry JSON data).
- **Tool failure**: a normal result with `"isError": true`. The tool ran
  and reported the failure in its `content`. Fix arguments or inputs; do
  not retry blindly.
- **Protocol failure**: a JSON-RPC `error`, for example `-32602` for an
  unknown tool. The tool never ran.

## stdio transport

- Messages are single-line UTF-8 JSON delimited by newlines: one JSON
  message per line, no embedded newlines, and no LSP-style `Content-Length`
  headers. Write requests to the server's stdin, read responses from its
  stdout.
- The server MAY log to stderr; stdout carries only protocol messages.
  The server should exit when its stdin closes.

Emergency shell pattern (no script, eyeball the ids in the output; the
`sleep`s keep the pipe open until the call finishes):

```bash
{ printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"shell","version":"1.0"}}}'
  sleep 2
  printf '%s\n' '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
                   '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"echo","arguments":{"message":"hi"}}}'
  sleep 3
} | npx -y @modelcontextprotocol/server-everything
```

Prefer `scripts/mcp_call.py`, which correlates responses by id, enforces
timeouts, silences server log noise, paginates `tools/list`, and shuts the
server down cleanly.

## Streamable HTTP with curl

One endpoint (e.g. `http://localhost:8083/mcp`), POSTed JSON-RPC. Required
on every POST: `Content-Type: application/json` and
`Accept: application/json, text/event-stream`.

```bash
BASE=http://localhost:3001/mcp   # example: PORT=3001 npx -y @modelcontextprotocol/server-everything streamableHttp

# 1. initialize; the response headers may carry Mcp-Session-Id
curl -sS -D /tmp/opencode/mcp-headers.txt -o /tmp/opencode/mcp-init.json \
  -X POST "$BASE" \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"curl","version":"1.0"}}}'

SESSION=$(grep -i '^mcp-session-id:' /tmp/opencode/mcp-headers.txt | tail -1 | tr -d '\r' | cut -d' ' -f2)
# Use the protocolVersion the server returned in the header below; the
# reference server's body is SSE-formatted, so grep it out:
# grep -o '"protocolVersion":"[^"]*"' /tmp/opencode/mcp-init.json | head -1

# 2. initialized notification (server answers 202 Accepted, no body)
curl -sS -X POST "$BASE" \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -H "Mcp-Session-Id: $SESSION" -H 'MCP-Protocol-Version: 2025-06-18' \
  -d '{"jsonrpc":"2.0","method":"notifications/initialized"}'

# 3. call a tool
curl -sS -X POST "$BASE" \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -H "Mcp-Session-Id: $SESSION" -H 'MCP-Protocol-Version: 2025-06-18' \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"echo","arguments":{"message":"hello"}}}'
```

Rules and gotchas:

- If the server returned a `Mcp-Session-Id`, send it on every subsequent
  request, along with `MCP-Protocol-Version: <negotiated version>`. A 404
  means the session expired. Start over at initialize.
- A request's response is HTTP 200 with either `Content-Type:
  application/json` (one JSON object) or `text/event-stream` (SSE-formatted
  lines; the JSON-RPC response is in a `data:` field, possibly after
  server notifications). Notifications get `202 Accepted` with no body.
  A `202` for a *request* is a protocol violation by the server.
- Send credentials via `Authorization` (or the server's documented header).
- GET (server-to-client stream) and DELETE (session teardown) are optional
  for simple tool calls; the stateless revision removed them.

## Stateless servers (2026-07-28)

Servers implementing only the current revision have no initialize and no
sessions. Detection: an `initialize` request fails with `-32601` (over
stdio) or the server rejects handshakes with a header-mismatch `400`
(`-32020`). Instead:

- Every request carries `_meta`:
  `{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientCapabilities":{},"io.modelcontextprotocol/clientInfo":{"name":"...","version":"..."}}`.
- Over HTTP, also send the headers `MCP-Protocol-Version: 2026-07-28`
  (must match the `_meta` value), `Mcp-Method: <method>`, and
  `Mcp-Name: <params.name or params.uri>` (required for `tools/call`).
- Results include `resultType` (`"complete"` or `"input_required"`); an
  `input_required` result must be retried with new input responses under a
  different JSON-RPC id.

`scripts/mcp_call.py` switches to this mode automatically when
`initialize` is rejected. `scripts/mock_stateless_server.py` imitates a
stateless server for testing (see [script.md](script.md)).

## SSE-only servers

The deprecated HTTP+SSE transport (e.g. JetBrains `.../sse`) cannot be
POSTed to directly: the client must first open a GET SSE stream, receive an
`endpoint` event with the real POST URI, and keep the stream open while
POSTing. Use the inspector instead:

```bash
npx -y @modelcontextprotocol/inspector@2.10.1 --cli http://localhost:64342/sse --transport sse --method tools/list
```

## Security notes

- A stdio MCP server executes with your full user privileges. Only run
  servers you or the user trust and that are already configured or
  explicitly approved; never pipe a server in from an untrusted source.
- Do not log or echo secrets (tokens in headers, `env` values). If a
  network block or missing credential stops you, report it. Do not look
  for ways around organizational controls.
