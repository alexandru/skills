#!/usr/bin/env python3
"""Stateless-era (2026-07-28) MCP server for validating mcp_call.py.

Speaks the stateless protocol: no initialize and no sessions; every
request must carry params._meta with the protocol version, and over HTTP
also the MCP-Protocol-Version, Mcp-Method, and (for tools/call) Mcp-Name
headers. Exposes one tool, echo. Requests missing the stateless rules
fail loudly, so a regression in mcp_call.py's stateless mode shows up as
a failed validation run.

Usage:
  mock_stateless_server.py             # stdio transport
  mock_stateless_server.py --port N    # HTTP at http://localhost:N/mcp

Over HTTP, request replies are SSE-formatted and the connection is held
open for a minute after the reply, like servers that keep the response
stream open instead of closing it; mcp_call.py must return as soon as the
reply arrives, not when the stream closes.

Requires Python 3.10+. Run the built-in tests with
`mock_stateless_server.py --self-test`.
"""

import json
import sys
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Final, TypeAlias, cast

Json: TypeAlias = dict[str, Any]

PROTOCOL: Final = "2026-07-28"
META_VERSION: Final = "io.modelcontextprotocol/protocolVersion"
HOLD_SECONDS: Final = 60

ECHO_TOOL: Json = {
    "name": "echo",
    "description": "Echo a message back.",
    "inputSchema": {
        "type": "object",
        "properties": {"message": {"type": "string"}},
        "required": ["message"],
    },
}


def error(id_: int | None, code: int, message: str, data: Json | None = None) -> Json:
    resp: Json = {"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": message}}
    if data is not None:
        resp["error"]["data"] = data
    return resp


def handle(msg: object) -> Json:
    """Return the JSON-RPC response for one request, enforcing stateless rules."""
    if not isinstance(msg, dict):
        return error(None, -32600, "request must be a JSON object")
    request = cast(Json, msg)
    id_ = request.get("id")
    if request.get("method") == "initialize":
        return error(id_, -32601, f"protocol {PROTOCOL} is stateless: no initialize method")
    params = request.get("params")
    meta = params.get("_meta") if isinstance(params, dict) else None
    if not (isinstance(meta, dict) and meta.get(META_VERSION)):
        return error(id_, -32602, f"stateless requests must carry params._meta.{META_VERSION}")
    assert isinstance(params, dict)  # guaranteed by the meta check above
    if request.get("method") == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": id_,
            "result": {
                "tools": [ECHO_TOOL],
                "resultType": "complete",
                "ttlMs": 60000,
                "cacheScope": "request",
            },
        }
    if request.get("method") == "tools/call":
        if params.get("name") != "echo":
            return error(id_, -32602, f"Unknown tool: {params.get('name')}")
        message = (params.get("arguments") or {}).get("message", "")
        return {
            "jsonrpc": "2.0",
            "id": id_,
            "result": {
                "content": [{"type": "text", "text": f"Echo: {message}"}],
                "resultType": "complete",
            },
        }
    return error(id_, -32601, f"method not found: {request.get('method')}")


def serve_stdio() -> None:
    for line in sys.stdin:
        stripped = line.strip()
        if not stripped:
            continue
        try:
            msg = json.loads(stripped)
        except ValueError:
            continue
        if isinstance(msg, dict) and "id" in msg:
            print(json.dumps(handle(msg), separators=(",", ":")), flush=True)


class Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)))
        except ValueError:
            self._reply_json(400, error(None, -32700, "invalid JSON"))
            return
        request = cast(Json, body) if isinstance(body, dict) else None
        id_ = request.get("id") if request is not None else None
        missing: list[str] = []
        if self.headers.get("MCP-Protocol-Version") != PROTOCOL:
            missing.append("MCP-Protocol-Version")
        if not self.headers.get("Mcp-Method"):
            missing.append("Mcp-Method")
        if request is not None and request.get("method") == "tools/call" and not self.headers.get("Mcp-Name"):
            missing.append("Mcp-Name")
        if missing:
            self._reply_json(400, error(id_, -32020, "HeaderMismatch", {"headers": missing}))
            return
        if request is None or "id" not in request:
            self._reply_json(202, None)
            return
        self._reply_sse(handle(request))

    def _reply_json(self, status: int, payload: Json | None) -> None:
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8") if payload is not None else b""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if data:
            self.wfile.write(data)

    def _reply_sse(self, payload: Json) -> None:
        event = f"event: message\ndata: {json.dumps(payload, separators=(',', ':'))}\n\n"
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        self.wfile.write(event.encode("utf-8"))
        self.wfile.flush()
        time.sleep(HOLD_SECONDS)


def main() -> None:
    if len(sys.argv) == 3 and sys.argv[1] == "--port":
        port = int(sys.argv[2])
        print(f"mock stateless MCP server on http://localhost:{port}/mcp", file=sys.stderr, flush=True)
        ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
    else:
        serve_stdio()


def run_tests() -> None:
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)


# --- built-in tests: run with `mock_stateless_server.py --self-test` ----------


def rpc(method: str, id_: int = 1, params: Json | None = None) -> Json:
    msg: Json = {"jsonrpc": "2.0", "id": id_, "method": method}
    if params is not None:
        msg["params"] = params
    return msg


def meta() -> Json:
    return {META_VERSION: PROTOCOL}


class HandleTest(unittest.TestCase):
    def test_initialize_rejected(self) -> None:
        resp = handle(rpc("initialize", params={"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {}}))
        self.assertEqual(resp["error"]["code"], -32601)

    def test_missing_meta_rejected(self) -> None:
        resp = handle(rpc("tools/list", params={}))
        self.assertEqual(resp["error"]["code"], -32602)

    def test_tools_list(self) -> None:
        resp = handle(rpc("tools/list", params={"_meta": meta()}))
        self.assertEqual(resp["result"]["tools"][0]["name"], "echo")
        self.assertEqual(resp["result"]["resultType"], "complete")

    def test_echo(self) -> None:
        resp = handle(rpc("tools/call", params={"name": "echo", "arguments": {"message": "hi"}, "_meta": meta()}))
        self.assertEqual(resp["result"]["content"][0]["text"], "Echo: hi")

    def test_unknown_tool(self) -> None:
        resp = handle(rpc("tools/call", params={"name": "nope", "_meta": meta()}))
        self.assertEqual(resp["error"]["code"], -32602)

    def test_unknown_method(self) -> None:
        resp = handle(rpc("prompts/list", params={"_meta": meta()}))
        self.assertEqual(resp["error"]["code"], -32601)

    def test_non_object_request(self) -> None:
        resp = handle([1, 2])
        self.assertEqual(resp["error"]["code"], -32600)


class ErrorTest(unittest.TestCase):
    def test_data_field_included(self) -> None:
        resp = error(5, -32020, "HeaderMismatch", {"headers": ["Mcp-Method"]})
        self.assertEqual(resp["error"]["data"]["headers"], ["Mcp-Method"])

    def test_no_data_field_by_default(self) -> None:
        resp = error(None, -32600, "bad request")
        self.assertNotIn("data", resp["error"])


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        run_tests()
    else:
        main()
