# MCP Inspector connection CLI (`mcpdo`)

`mcpdo` is the connection-oriented CLI shipped by the official Inspector.
It uses a local daemon to retain named connections between invocations.
The client is experimental; use the pinned release and validate it against
the required server before relying on a workflow.

## Run the pinned client

Requires Node >= 22.19.0 and an installed or retrievable package. No LLM
API key is needed:

```bash
npx -y --package @modelcontextprotocol/inspector@2.10.1 mcpdo --help
```

In the examples below, prefix each `mcpdo` command with
`npx -y --package @modelcontextprotocol/inspector@2.10.1` unless that release
is already installed. Put global options such as `--format json`,
`--connection`, and `--config` before the subcommand.

## Connect, inspect, call, disconnect

For a compatible `mcpServers` config, connect an existing entry without
editing its source file. Choose a connection name unique to your session:

```bash
mcpdo --format json --connection task-browser --config /path/to/mcp.json \
  connect browser --era auto
mcpdo --format json @task-browser tools/list
mcpdo --format json @task-browser tools/call navigate_page '{"url":"https://example.com"}'
mcpdo --format json @task-browser tools/call take_screenshot '{}'
mcpdo --format json disconnect task-browser
```

Inspect each response before issuing the next command. `tools/list` merges
all pages; it does not need a `--cursor` flag. Calls accept one JSON object
as the tool arguments. For unknown options, use the subcommand's `--help`.

Ad-hoc connections preserve separate server arguments; the `--` belongs
before the server command and its flags. These targets must already be
configured or approved:

```bash
mcpdo --format json --connection task-browser connect --era auto --transport stdio -- \
  npx -y chrome-devtools-mcp@latest --headless --isolated
mcpdo --format json --connection task-ide connect http://localhost:64342/stream \
  --transport http --era auto
```

Use `--transport sse` for a configured SSE endpoint. Supply the configured
`--cwd`, environment (`-e KEY=VALUE`), and HTTP headers (`--header 'Name: Value'`)
when needed; prefer a protected config file for secret values.

## Pending results and connection lifetime

`--format json` writes the payload to stdout, not a `{result: ...}` wrapper.
Diagnostics go to stderr; keep the two streams separate. Exit 0 alone does
not establish completion:

- **`pendingAuth: true`:** the connection is not usable. If sign-in is
  permitted, relay `authUrl` as literal text at the end of your reply, ask
  the user to sign in, and end the turn. Do not poll. After their confirmation,
  use `mcpdo --format json connections/show @task-browser` to complete sign-in.
- **`elicitationPending`:** the tool call remains parked in the daemon.
  Inspect its question and schema, obtain the required answer, then use
  `mcpdo --format json elicitation/respond ID '{"field":"value"}'`, or
  `elicitation/respond ID --decline` / `--cancel`. Do not resubmit the tool call.
- **`isError: true` or `error`:** apply the failure policy in [SKILL.md](../SKILL.md).

Connections can transparently reconnect after transport loss. A new stdio
process need not retain browser or workspace state; inspect that state
before continuing a dependent workflow. Reuse connections only when their
ownership and state are known, and disconnect those you create.

## Validation

After changing this skill:

1. Run the pinned client's `--help`, `connect --help`, `tools/call --help`,
   and `elicitation/respond --help`; check the documented option forms.
2. Against a configured or explicitly approved test server, connect once,
   list tools, perform a benign schema-valid call, inspect the result, and
   disconnect. Verify that dependent calls retain state and that argument
   values containing spaces arrive intact.
3. Exercise the manual HTTP sequence against such a server, checking both
   JSON and SSE responses, session/version headers, and pending results.
   Report any server or transport that was not exercised.

## Sources

- [Pinned package and runtime requirement](https://github.com/modelcontextprotocol/inspector/blob/2.10.1/package.json)
- [Connection CLI documentation](https://github.com/modelcontextprotocol/inspector/blob/2.10.1/clients/mcpdo/README.md)
- [Official agent workflow](https://github.com/modelcontextprotocol/inspector/blob/2.10.1/skills/mcpdo/SKILL.md)
- [CLI argument definitions](https://github.com/modelcontextprotocol/inspector/blob/2.10.1/clients/mcpdo/src/connection/mcp.ts)
