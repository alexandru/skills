---
name: mcp-access
description: "Call MCP (Model Context Protocol) servers when the harness's native MCP tools are unavailable, restricted, or unsupported. Fallback chain: harness MCP tools, then the MCP Inspector CLI, then raw JSON-RPC over stdio or HTTP with a bundled script and curl recipes. Use for listing or calling tools (tools/list, tools/call) on stdio servers such as chrome-devtools-mcp and persistent servers such as JetBrains IDEs and Metals, and for debugging MCP connectivity."
---

# MCP access without native MCP tools

Use this skill when an MCP task exists (list tools, call a tool) but the
harness's MCP integration is missing, restricted, or lacks the server you
need. If native MCP tools already work, use them and stop here.

## Fallback strategy: try tiers in order, stop at the first that works

**Tier 1, native MCP tools.** If your harness exposes MCP tools for the
server (commonly named `<server>_<tool>` or `mcp__server__tool`), use them.
If they are absent, disabled, or blocked, continue.

**Tier 2, the MCP Inspector CLI.** The official MCP debugging tool; needs
no LLM API key. Requires Node >= 22.19 and npm registry access:

```bash
# stdio server: server command first, then '--', then inspector flags
npx -y @modelcontextprotocol/inspector@2.10.1 --cli npx -y chrome-devtools-mcp@latest -- --method tools/list
npx -y @modelcontextprotocol/inspector@2.10.1 --cli npx -y chrome-devtools-mcp@latest -- --method tools/call --tool-name navigate_page --tool-args-json '{"url":"https://example.com"}'
# HTTP server
npx -y @modelcontextprotocol/inspector@2.10.1 --cli http://localhost:8083/mcp --transport http --method tools/list
```

Exit codes: 0 success, 3 authentication required, 4 server unreachable,
5 the tool ran and returned `isError: true`. Results go to stdout,
diagnostics to stderr. If Node is too old or npm is blocked, continue.

**Tier 3, raw JSON-RPC via the bundled script.** Needs only Python 3.10+.
It handles the initialize handshake, protocol-version negotiation, and the
stateless 2026-07-28 protocol automatically. Paths below are relative to
this skill's directory:

```bash
python3 scripts/mcp_call.py stdio --cmd 'npx -y chrome-devtools-mcp@latest' list
python3 scripts/mcp_call.py stdio --cmd 'npx -y chrome-devtools-mcp@latest' call navigate_page '{"url":"https://example.com"}'
python3 scripts/mcp_call.py http http://localhost:8083/mcp list
python3 scripts/mcp_call.py http http://localhost:64342/stream call get_file_content '{"path":"README.md"}'
```

Exit codes: 0 success, 1 tool or protocol failure (read the printed JSON),
2 transport or usage error. HTTP servers can also be called with plain
curl; see [references/protocol.md](references/protocol.md).

**Stop and report when** the server command itself cannot be installed or
started, the network blocks it, or credentials are missing. Do not try to
work around network or policy blocks; report what you tried and what failed.

## Steps

1. Find the server definition in the harness configuration (see
   [references/servers.md](references/servers.md) for where to look).
   A `command` array means a stdio server (use it after `--cmd`, joined with
   spaces); a `url` means an HTTP server (use it as the URL/`--server-url`).
2. Run `list` first, read each tool's `inputSchema`, then build one JSON
   object with every `required` field and `call` it.
3. For slow-starting or persistent servers (Metals, browsers, IDEs), batch
   every op you need into **one** `mcp_call.py` invocation (tier 3), `list
   call a '{}' call b '{}'`. The server process starts once and reuses its
   state. The inspector (tier 2) runs one method per command instead.
4. On failure, read the printed JSON: `isError: true` means the tool
   executed and failed; an `error` object means a protocol-level failure
   (unknown tool, invalid arguments, no tools capability).

## Rules

- Always `list` before `call` unless the tool name and arguments are
  already known.
- Tool arguments are a single JSON object matching the tool's `inputSchema`.
- Only contact servers already configured or explicitly approved by the
  user. A stdio MCP server runs with your full user privileges; never pipe
  one in from an untrusted source.
- The inspector version is pinned deliberately (supply-chain hygiene). To
  use a newer release, check `npm view @modelcontextprotocol/inspector version`.
- SSE-only endpoints (`/sse`) cannot be POSTed to directly; use the
  inspector with `--transport sse`.

## References

- [references/inspector.md](references/inspector.md): MCP Inspector CLI
  install, syntax rules, tools/list and tools/call, auth, output, exit
  codes.
- [references/protocol.md](references/protocol.md): JSON-RPC shapes,
  protocol revisions and negotiation, initialize handshake, stdio framing,
  curl recipes for streamable HTTP, SSE caveat.
- [references/servers.md](references/servers.md): recipes for
  chrome-devtools-mcp, JetBrains IDEs, Metals, and the MCP test server;
  finding server definitions; persistent-server patterns.
- [references/script.md](references/script.md): `mcp_call.py` ops,
  options, output, exit codes, troubleshooting.
