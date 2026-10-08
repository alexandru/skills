---
name: mcp-access
description: "Calls MCP (Model Context Protocol) servers when native MCP tools are unavailable or unsupported, using the MCP Inspector connection CLI or a manual JSON-RPC fallback specification. Use for listing and calling tools over stdio or HTTP, retaining state across calls, and diagnosing MCP connectivity."
---

# MCP access without native MCP tools

Use native MCP tools when they support the required workflow. Otherwise use
the MCP Inspector's `mcpdo` connection CLI, which keeps one connection alive
across calls. If that client is unavailable or cannot support the server,
use the [manual protocol specification](references/protocol.md) with tools
such as curl or an interactive process tool.

## Workflow

1. Find an already configured or explicitly approved server in the
   [harness configuration](references/servers.md). Preserve its argument
   boundaries, environment, working directory, URL, and headers.
2. Follow [the connection CLI reference](references/inspector.md) to connect.
   Use an explicit connection name for every command; retain that connection
   while inspecting results and deciding subsequent calls.
3. List tools, including all pages, unless the tool name and schema are
   already known. Pass one JSON object matching `inputSchema`, including
   every required field.
4. Inspect the result, not just the exit status. Pending authentication,
   elicitation, or an incomplete result is not successful completion.
5. Disconnect connections you created when finished. Do not stop a shared
   daemon or close another session's connections.

## Failure policy

- **Client unavailable or incompatible:** manual access is an alternative
  only if the available tools can maintain the required transport and
  session. Follow the protocol specification; do not approximate handshakes
  with sleeps or build a general-purpose client.
- **Tool or protocol error:** read the result and correct the named tool,
  arguments, or documented protocol mismatch. Do not change clients or
  retry blindly. After uncertain delivery, do not repeat a mutating call
  without establishing whether it executed.
- **Missing server credentials, server startup failure, or denied server
  access:** stop and report what failed. Fallbacks do not bypass network or
  authorization controls, including native-tool permission denials.

A stdio MCP server runs with your full user privileges. Only run trusted,
configured or approved server commands, and keep credentials out of logs.

## References

- [references/inspector.md](references/inspector.md): pinned connection CLI,
  stateful calls, pending results, and validation.
- [references/protocol.md](references/protocol.md): manual JSON-RPC, version
  negotiation, stdio, HTTP, and completion requirements.
- [references/servers.md](references/servers.md): server definitions and
  server-specific connection requirements.
