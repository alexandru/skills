# MCP Inspector CLI

The MCP Inspector (`@modelcontextprotocol/inspector`) is the official
debugging and testing tool for MCP servers. Its CLI mode calls
`tools/list` and `tools/call` directly, with no LLM API key. This skill
standardizes on it for the external-tool tier.

Current major version: 2.x, a rewrite of the 1.x line. Much of the older
1.x syntax circulating online is wrong for 2.x. Use the forms below.

## Contents

- [Install](#install)
- [Syntax rules](#syntax-rules)
- [Listing tools](#listing-tools)
- [Calling tools](#calling-tools)
- [URL-based servers (HTTP and SSE)](#url-based-servers-http-and-sse)
- [Output and exit codes](#output-and-exit-codes)
- [Authentication](#authentication)
- [Saved servers (config and catalog)](#saved-servers-config-and-catalog)
- [Troubleshooting](#troubleshooting)

## Install

```bash
npx -y @modelcontextprotocol/inspector@2.10.1   # one-off run, version pinned
npm install -g @modelcontextprotocol/inspector  # persistent install, provides the mcp-inspector binary
```

- `-y` suppresses the first-run npx install prompt, which otherwise hangs
  unattended runs.
- Pin the version (as above) for reproducible, supply-chain-safer runs;
  check for newer with `npm view @modelcontextprotocol/inspector version`.
- Requires **Node >= 22.19** (npm only warns on older Node, and the tool
  then fails in confusing ways). Check with `node --version`.
- There is no official Python install; the PyPI package `mcp-inspector`
  is unrelated. Do not use it.

## Syntax rules

```
npx -y @modelcontextprotocol/inspector@2.10.1 --cli <target> [flags]
```

- The mode flag `--cli` comes first.
- The target must precede all flags: a stdio server command (e.g.
  `node build/index.js`, `npx -y some-mcp@latest`) or a URL. A target
  placed after a flag is silently dropped.
- When the server command itself has flags, end it with `--`; everything
  before `--` is the server command, everything after is inspector flags:
  ```bash
  npx -y @modelcontextprotocol/inspector@2.10.1 --cli node build/index.js --config ./server.conf -- --method tools/list
  ```
- Key flags: `--method <method>`, `--transport <stdio|http|sse>`,
  `--server-url <url>`, `--config <path>`, `--catalog <path>`,
  `--header 'Name: Value'` (repeatable).

## Listing tools

```bash
npx -y @modelcontextprotocol/inspector@2.10.1 --cli npx -y chrome-devtools-mcp@latest -- --method tools/list
npx -y @modelcontextprotocol/inspector@2.10.1 --cli http://localhost:8083/mcp --transport http --method tools/list
```

`--method initialize` is a cheap connect-only probe that prints
`{serverInfo, protocolVersion, capabilities, instructions}`. Use it to
check that a server is reachable before calling tools.

## Calling tools

```bash
# simple scalar arguments: repeat --tool-arg key=value (values are JSON-parsed when they parse)
npx -y @modelcontextprotocol/inspector@2.10.1 --cli npx -y chrome-devtools-mcp@latest -- \
  --method tools/call --tool-name navigate_page --tool-arg url=https://example.com

# structured arguments: one JSON object
npx -y @modelcontextprotocol/inspector@2.10.1 --cli npx -y chrome-devtools-mcp@latest -- \
  --method tools/call --tool-name navigate_page --tool-args-json '{"url":"https://example.com"}'
```

- `--tool-args-json '<json object>'` passes the object verbatim; prefer it
  for structured arguments. It is mutually exclusive with `--tool-arg`.
- Other methods: `resources/list`, `resources/read` (`--uri`),
  `prompts/list`, `prompts/get` (`--prompt-name`, `--prompt-args`), plus
  `tools/list` pagination via `--cursor`. There is no generic `--params`
  flag.

## URL-based servers (HTTP and SSE)

```bash
npx -y @modelcontextprotocol/inspector@2.10.1 --cli http://localhost:8083/mcp --transport http --method tools/list
npx -y @modelcontextprotocol/inspector@2.10.1 --cli http://localhost:64342/sse --transport sse --method tools/list
```

- Always pass `--transport` explicitly for URLs. Without it the inspector
  guesses from the path suffix only: a path ending in `/mcp` counts as
  http and one ending in `/sse` as sse, and anything else errors.
- `http` here means the streamable HTTP transport.

## Output and exit codes

- Results go to stdout; logs and errors go to stderr. Never merge them
  (`2>&1`) before piping stdout to `jq`.
- A `MCP error -32001: Request timed out` line on stderr (the inspector
  asking the calling client for roots) can appear even on successful runs;
  judge success by the exit code and stdout, not by stderr silence.
- `--format json` emits a single JSON object (`{"result": ...}`) instead of
  pretty text; `-q` prints only the payload; `--output FILE` writes the
  result to a file.
- Exit codes:

| Code | Meaning |
|------|---------|
| 0 | success |
| 1 | usage or unexpected error |
| 3 | server requires authentication (401/403) |
| 4 | server unreachable (DNS, refused, timeout) |
| 5 | tool error (`isError: true`, or tool not found) |

On any non-zero exit the last stderr line is a JSON `ErrorEnvelope`
(`{"error":{"code":"...","message":"..."}}`). Exit 3 or 4 means the tier
failed, so fall back to the raw protocol tier. Exit 5 means the tool ran
and failed, so fix the arguments.

## Authentication

- Bearer/custom headers: `--header 'Authorization: Bearer <token>'`.
- OAuth: `--client-id`, `--client-secret`, `--callback-url`,
  `--wait-for-auth <sec>`, `--stored-auth-only`, `--relogin`. There is no
  `--token` flag.
- It does not scrub tokens embedded in URLs or server command args; pass
  secrets with `--header` instead.

## Saved servers (config and catalog)

- `--config <path>`: read-only session file with server definitions
  (`stdio` command/env or `http`/`sse` URL with headers).
- `--catalog <path>`: writable catalog of servers (default
  `~/.mcp-inspector/mcp.json`, override with `MCP_CATALOG_PATH`); combine
  with `--server <name>` under `--cli` to skip re-typing commands.
- Both are mutually exclusive with an ad-hoc target on the command line.

## Troubleshooting

- **`EBADENGINE` warning or obscure crash**: Node < 22.19. Check
  `node --version`; if you cannot upgrade, use the raw-protocol tier
  (`scripts/mcp_call.py`) instead.
- **Target silently ignored**: it was placed after a flag. Targets come
  first; use `--` when the server command has its own flags.
- **Auth loop or 401**: pass `--header 'Authorization: Bearer ...'`, or
  for OAuth servers use `--client-id` and `--wait-for-auth`.
- **`--transport` error on a URL**: pass it explicitly; URL inference only
  recognizes `/mcp` and `/sse` path suffixes.
