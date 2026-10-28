# Server recipes and finding server definitions

Where to find server definitions in harness configuration, and connection
requirements for chrome-devtools-mcp, JetBrains IDEs, and Metals. Use the
[connection CLI reference](inspector.md) for command syntax.

## Contents

- [Finding server definitions](#finding-server-definitions)
- [chrome-devtools-mcp](#chrome-devtools-mcp)
- [JetBrains IDEs (IntelliJ IDEA and others)](#jetbrains-ides-intellij-idea-and-others)
- [Metals](#metals)
- [Sources](#sources)

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

Preserve the executable and each argument separately. For a compatible
`mcpServers` file, pass it read-only with `--config`. For other formats,
translate only the selected entry to a protected temporary config or pass
the equivalent connection options; do not rewrite the harness config.
Keep configured environment variables, working directory, and HTTP headers.
An argument containing spaces remains one argument, not several tokens.

## chrome-devtools-mcp

Google's official DevTools MCP server; stdio transport; requires Node LTS
and a Chrome install (Google Chrome or Chrome for Testing).

Use the configured command, commonly `npx -y chrome-devtools-mcp@latest`.
An approved isolated headless session can use `--headless --isolated`;
`--browser-url` attaches to an already-running Chrome with remote debugging.
Retain one named connection while navigating, inspecting, clicking, and
taking screenshots so later calls see the same browser state.

## JetBrains IDEs (IntelliJ IDEA and others)

The built-in MCP Server plugin ships in IDE 2025.2 and later (enable it in
Settings | Tools | MCP Server). The IDE must be running. State (index,
open files) lives in the IDE, so per-call connections are fine.

Copy the endpoint and headers from the IDE's generated client configuration;
do not infer the port from the product name. IntelliJ IDEA commonly exposes
`http://localhost:64342/stream` (streamable HTTP) and `.../sse` (SSE).
Preserve `IJ_MCP_SERVER_PROJECT_PATH` and any configured authentication header.
Prefer the built-in server's HTTP endpoint over the deprecated
`@jetbrains/mcp-proxy` package.

## Metals

The Scala language server ships an MCP server (since Metals 1.5.3; the
standalone `metals-mcp` launcher with `--transport stdio` since 1.6.7).

- Editor mode: `metals.startMcpServer = true`; the endpoint is
  `http://localhost:<port>/mcp` (port written to `.metals/mcp.json`).
- Standalone: the configured `metals-mcp --workspace . --transport stdio`
  command runs the MCP server. Preserve its workspace argument and cwd.

Caveats: wait for indexing before search tools; call `import-build` after
build changes; search results cap at 100 by default. JVM startup plus
indexing makes cold calls slow. Retain the connection rather than restarting
the server per tool call; inspect the live `inputSchema` rather than assuming
a fixed tool roster or argument format.

## Sources

- [Chrome DevTools MCP](https://github.com/ChromeDevTools/chrome-devtools-mcp)
- [JetBrains MCP server](https://www.jetbrains.com/help/idea/mcp-server.html)
- [Metals MCP server](https://scalameta.org/metals/docs/features/mcp/)
