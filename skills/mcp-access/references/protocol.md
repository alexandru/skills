# Manual MCP access specification

Use this specification when the packaged client cannot be used and the
available tools can exchange messages correctly. It covers tool discovery
and calls, not a general-purpose MCP client. Apply the failure policy in
[SKILL.md](../SKILL.md); a different transport does not grant authorization.

## Contents

- [Message contract](#message-contract)
- [Choose a protocol revision](#choose-a-protocol-revision)
- [Tool operations](#tool-operations)
- [stdio](#stdio)
- [Streamable HTTP and curl](#streamable-http-and-curl)
- [SSE-only endpoints](#sse-only-endpoints)
- [Completion and cleanup](#completion-and-cleanup)
- [Sources](#sources)

## Message contract

- Send one JSON-RPC 2.0 object per message, not a batch array. A request has
  `jsonrpc: "2.0"`, a unique non-null string or integer `id`, `method`, and
  optional object `params`. A notification omits `id`.
- A response repeats the request's `id`, has no `method`, and contains
  exactly one of `result` or `error`. Matching an ID alone is insufficient:
  an incoming server request may use that same ID.
- Keep notifications separate from responses, and inspect the complete
  matched response before deciding the next operation. Bound each wait;
  transport exit status is not the MCP operation's completion status.

## Choose a protocol revision

Use the server's documented revision or the official discovery/fallback
rules linked below. Do not infer a revision from an arbitrary HTTP 400 or
a missing method. Use only revisions whose message contract you understand.

### Initialize-era: 2025-06-18 and 2025-11-25

Send `initialize`, wait for its response, check the returned version and
capabilities, then send `notifications/initialized`. Continue only if the
selected version is supported by the manual workflow:

```json
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"manual-client","version":"1.0.0"}}}
```

```json
{"jsonrpc":"2.0","method":"notifications/initialized"}
```

The server may return a different supported version. Do not substitute the
proposed version for the returned version. Empty capabilities mean that no
sampling, elicitation, or roots support is advertised.

### Stateless: 2026-07-28

There is no `initialize`, initialized notification, or protocol session.
Every request carries `params._meta` with the version and client capabilities;
include client identity as recommended by the specification:

```json
{"jsonrpc":"2.0","id":1,"method":"server/discover","params":{"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientCapabilities":{},"io.modelcontextprotocol/clientInfo":{"name":"manual-client","version":"1.0.0"}}}}
```

Discovery returns `result.supportedVersions` and `result.capabilities`.
Choose a mutually supported revision. Error `-32022` carries
`error.data.supported`; do not select an unfamiliar revision merely because
the server lists it. Preserve caller metadata when adding protocol fields.

## Tool operations

After choosing the protocol mode, list tools:

```json
{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}
```

Read `result.tools` and each tool's `inputSchema`. If `result.nextCursor`
is present, issue another request with a new ID and
`params.cursor` equal to that exact value; merge pages until it is absent.
Then call the selected tool with a schema-valid JSON object:

```json
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"echo","arguments":{"message":"hello"}}}
```

These two messages show initialize-era bodies. For the stateless revision,
add the same required `_meta` to each `params` object, including cursor
requests. Do not send a tool call before inspecting its schema unless the
name and schema are already known.

## stdio

Launch the configured command with its original argument boundaries,
environment, and cwd using a tool that can retain an interactive process.
Write single-line UTF-8 JSON followed by a newline to stdin; read stdout as
newline-delimited messages. There are no `Content-Length` headers. Keep
stderr separate for server diagnostics.

Retain both streams and the process between dependent calls. An interactive
tool must allow reading a response before writing the next request; fixed
sleep pipelines do not satisfy this contract. If your tools cannot maintain
that interaction, report the limitation.

## Streamable HTTP and curl

POST each message separately to the configured endpoint. Include
`Content-Type: application/json`, `Accept: application/json, text/event-stream`,
and the configured authentication/project headers. Do not put credentials
in the URL.

For an initialize-era server, this is the initial request (`URL` must be
set to the configured endpoint):

```bash
curl --silent --show-error --no-buffer --include --max-time 60 \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  --data-binary '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"manual-client","version":"1.0.0"}}}' \
  "$URL"
```

On every subsequent POST, include `MCP-Protocol-Version` with the negotiated
value and, if issued by the initialize response, `Mcp-Session-Id`. This
includes the initialized notification and any replies to server requests.
A notification or client response is accepted with HTTP 202 and no body.
For an expired session (HTTP 404), initialize a new session without the old
ID; reconcile any uncertain tool execution before resuming.

For a stateless server, send `MCP-Protocol-Version` matching `_meta`,
`Mcp-Method` matching `method`, and, for `tools/call`, `Mcp-Name` matching
`params.name`. Do not send a session header. A tool-list request is:

```bash
curl --silent --show-error --no-buffer --include --max-time 60 \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H 'MCP-Protocol-Version: 2026-07-28' -H 'Mcp-Method: tools/list' \
  --data-binary '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientCapabilities":{},"io.modelcontextprotocol/clientInfo":{"name":"manual-client","version":"1.0.0"}}}}' \
  "$URL"
```

Header/body mismatches produce `HeaderMismatch` (`-32020`, HTTP 400).
For names requiring header encoding, follow the linked HTTP specification's
value-encoding rules rather than changing the name in the JSON body.

A request response is one JSON object (`application/json`) or an SSE stream
(`text/event-stream`). For SSE, collect `data:` lines within each event,
join them with newlines, and parse that JSON object. Inspect events until the
matched response arrives; progress notifications are not completion.
HTTP 202 without a response body does not complete a tool request.

Curl may wait for EOF after a matched response. A curl timeout after a
complete response need not mean the operation failed; inspect the message,
not only the exit code. Closing a modern SSE response stream before the
final response cancels that request. Do not blindly replay it.

## SSE-only endpoints

The deprecated HTTP+SSE transport needs a live GET event stream. Receive
its `endpoint` event, resolve the POST URI against the configured server,
then POST requests there while reading responses on the GET stream. Verify
that the resolved endpoint is authorized; do not follow an unapproved origin.
An endpoint ending in `/sse` is not itself a JSON-RPC POST endpoint.
If your tools cannot maintain both channels, report the limitation.

## Completion and cleanup

- In initialize-era mode, answer an incoming `ping` request promptly with
  `{"jsonrpc":"2.0","id":"server-ping","result":{}}`, substituting its exact
  ID. Reply to other unsupported server requests with `-32601` and the same
  ID. On HTTP, POST those responses separately while retaining the SSE read.
  Stateless servers do not send independent server requests; `ping` is not
  part of that revision.
- A JSON-RPC `error` is a failure. A tool result with `isError: true` is also
  a failure, even though it arrived in a normal response.
- For the stateless revision, `resultType: "complete"` marks completion.
  `resultType: "input_required"` is incomplete: inspect `inputRequests` and
  `requestState`. Only fulfill input requests for capabilities you advertised
  and can actually support. Retry the original operation with the requested
  `inputResponses`, the exact opaque `requestState` if present, and a new ID.
  A state-only retry needs no input responses. Otherwise report the unsupported
  interaction; do not run dependent operations or claim success. Do not
  interpret or alter the state, or reuse it for another operation.
- Close a stdio child's stdin, wait for exit, and terminate only the process
  you own if it does not exit. For initialize-era HTTP, send DELETE with the
  session ID when finished; HTTP 405 means the server does not support client
  session termination. Stateless HTTP needs no session DELETE.

## Sources

- [JSON-RPC 2.0](https://www.jsonrpc.org/specification)
- [Initialize-era lifecycle and version negotiation](https://modelcontextprotocol.io/specification/2025-06-18/basic/lifecycle)
- [Initialize-era HTTP and sessions](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)
- [Initialize-era ping](https://modelcontextprotocol.io/specification/2025-06-18/basic/utilities/ping)
- [Stateless versioning](https://modelcontextprotocol.io/specification/2026-07-28/basic/versioning)
- [Server discovery](https://modelcontextprotocol.io/specification/2026-07-28/server/discover)
- [stdio and backward-compatible discovery](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/stdio)
- [Stateless HTTP, header encoding, and compatibility](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http)
- [Incomplete results and retries](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr)
