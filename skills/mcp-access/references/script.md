# mcp_call.py reference

`scripts/mcp_call.py` is a Python 3.10+ (stdlib-only, POSIX) MCP client for
the raw-protocol tier. It speaks stdio and streamable HTTP. It performs
the initialize handshake, negotiates the protocol version, and
auto-switches to the stateless 2026-07-28 protocol when a server has no
handshake. It paginates `tools/list`, correlates responses by id, and
shuts the server down.

Results print to stdout as pretty JSON; progress and errors print to
stderr prefixed with `[mcp]`.

## Contents

- [Synopsis](#synopsis)
- [Operations](#operations)
- [Options](#options)
- [Output and exit codes](#output-and-exit-codes)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)
- [Validating changes to this skill](#validating-changes-to-this-skill)

## Synopsis

```text
mcp_call.py stdio --cmd 'SERVER COMMAND' [options] op [op ...]
mcp_call.py http URL [--header 'NAME: VALUE'] [options] op [op ...]
```

Ops run in the order given, in one server session.

## Operations

| Op | Meaning |
|----|---------|
| `list` | `tools/list` (all pages merged); prints `{"tools":[...]}` |
| `call TOOL` | `tools/call` with no `arguments` |
| `call TOOL '{"k":"v"}'` | `tools/call` with that JSON object as `arguments` |
| `raw METHOD` | any JSON-RPC request, e.g. `raw resources/list` |
| `raw METHOD '{"k":"v"}'` | same, with params |

Arguments/params must be a single JSON object (starting with `{`).

## Options

| Option | Default | Meaning |
|--------|---------|---------|
| `--cmd COMMAND` | (required, stdio) | server command line, shell-quoted |
| `--header 'NAME: VALUE'` | none (http) | extra HTTP header, repeatable (auth) |
| `--timeout SECS` | 300 | seconds to wait per response; raise for JVM/browser/indexing servers |
| `--protocol-version VERSION` | 2025-06-18 | version proposed in `initialize` |
| `--verbose` | off | log every protocol message to stderr |

## Output and exit codes

- stdout: one pretty JSON blob per op (tool results, error responses, or
  the merged tool list).
- stderr: `[mcp]` progress lines; the server's own logs/stderr pass
  through untouched.
- Exit codes: `0` all ops succeeded; `1` a tool reported `isError: true`
  or a JSON-RPC error came back (the run stops at the first failure);
  `2` usage, transport, or handshake failure; `130` interrupted.

## Examples

```bash
# stdio: list, then call with arguments
python3 scripts/mcp_call.py stdio --cmd 'npx -y chrome-devtools-mcp@latest' list
python3 scripts/mcp_call.py stdio --cmd 'npx -y chrome-devtools-mcp@latest' \
  call navigate_page '{"url":"https://example.com"}'

# batch ops for slow-starting servers: one process, many calls
python3 scripts/mcp_call.py stdio --cmd 'metals-mcp --workspace . --transport stdio' --timeout 900 \
  call import-build '{}' call inspect '{"position":"file:/x.scala#42"}' call get-docs '{}'

# HTTP with auth
python3 scripts/mcp_call.py http http://localhost:64342/stream \
  --header 'Authorization: Bearer TOKEN' list call get_file_content '{"path":"README.md"}'

# anything else on the protocol
python3 scripts/mcp_call.py http http://localhost:8083/mcp raw resources/list
```

## Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| `the server ... exited before responding` | Server command failed; run it alone to see its error (bad package name, missing Chrome, wrong path). |
| `timed out waiting for the server to respond` | Slow startup or long-running tool; raise `--timeout`, watch stderr for the server's own progress logs. |
| `HTTP 401/403 ... requires authentication` | Pass `--header 'Authorization: Bearer <token>'` (or the server's documented scheme). |
| `HTTP 404 ... wrong URL path or the session expired` | Re-run; if the path ends in `/sse`, it is an SSE endpoint. Use the MCP Inspector with `--transport sse`. |
| `server returned HTTP 202 for a request` | Not a streamable HTTP MCP endpoint, or an unusual server; fall back to the inspector. |
| `switching to stateless mode` (stderr) | Expected: the server speaks the 2026-07-28 protocol; no action needed. |
| `server wrote a non-JSON line to stdout (ignored)` | Server log noise on stdout; harmless, or use `--verbose` to see everything. |
| `tools/call returned a protocol error` | Unknown tool or invalid arguments; run `list` and match `inputSchema` exactly. Some servers report unknown tools as a normal result with `isError: true` instead. Read the `content` text either way. |
| `arguments ... must be a single JSON object` | Quote the JSON in the shell and make it an object: `call echo '{"message":"hi"}'`. |

## Validating changes to this skill

Run the built-in unit tests first (offline, needs only Python 3.10), then
the live checks against the official test server (needs network and
Node), then the stateless HTTP check against the bundled mock:

```bash
python3 skills/mcp-access/scripts/mcp_call.py --self-test
python3 skills/mcp-access/scripts/mock_stateless_server.py --self-test

python3 skills/mcp-access/scripts/mcp_call.py stdio --cmd 'npx -y @modelcontextprotocol/server-everything' list
python3 skills/mcp-access/scripts/mcp_call.py stdio --cmd 'npx -y @modelcontextprotocol/server-everything' call echo '{"message":"hello"}'
PORT=3001 npx -y @modelcontextprotocol/server-everything streamableHttp &
python3 skills/mcp-access/scripts/mcp_call.py http http://localhost:3001/mcp list
python3 skills/mcp-access/scripts/mcp_call.py http http://localhost:3001/mcp call echo '{"message":"over http"}'

# stateless over HTTP (the self-test covers stateless stdio)
python3 skills/mcp-access/scripts/mock_stateless_server.py --port 3002 &
python3 skills/mcp-access/scripts/mcp_call.py http http://localhost:3002/mcp \
  list call echo '{"message":"stateless over http"}'
```

The stateless HTTP run must print a `[mcp] ... switching to stateless
mode` line on stderr and finish in seconds: the mock holds each reply
stream open for a minute, so a regression to reading the response to EOF
would time out instead. Stop the background servers afterwards. Also
re-run the curl sequence in [protocol.md](protocol.md) against the test
server, and one inspector command from [inspector.md](inspector.md).
