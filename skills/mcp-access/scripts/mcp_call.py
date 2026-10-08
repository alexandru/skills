#!/usr/bin/env python3
"""Call MCP servers directly: stdio or streamable HTTP, no MCP host required.

Examples:
  mcp_call.py stdio --cmd 'npx -y chrome-devtools-mcp@latest' list
  mcp_call.py stdio --cmd 'npx -y chrome-devtools-mcp@latest' call navigate_page '{"url":"https://example.com"}'
  mcp_call.py stdio --cmd 'metals-mcp --workspace . --transport stdio' list call inspect '{}' call get-docs '{}'
  mcp_call.py http http://localhost:8083/mcp list
  mcp_call.py http http://localhost:64342/stream --header 'Authorization: Bearer TOKEN' call some_tool '{"arg":"value"}'

Protocol handling is automatic:
  - Handshake-era servers (revisions 2024-11-05 .. 2025-11-25): initialize,
    notifications/initialized, then the requested operations.
  - Stateless-era servers (revision 2026-07-28+): initialize is rejected, so
    every request carries the protocol version and client info in _meta plus
    the Mcp-Method / Mcp-Name HTTP headers instead.

Exit codes: 0 success, 1 tool or protocol failure, 2 usage or transport failure.

Requires Python 3.10+. Run the built-in tests with `mcp_call.py --self-test`.
"""

import argparse
import contextlib
import io
import json
import os
import select
import shlex
import signal
import socket
import subprocess
import sys
import time
import unittest
import urllib.error
import urllib.request
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from http.client import HTTPResponse
from typing import Any, Final, NoReturn, Protocol, TypeAlias, cast

Json: TypeAlias = dict[str, Any]
HeaderList: TypeAlias = Sequence[tuple[str, str]]

DEFAULT_PROTOCOL_VERSION: Final = "2025-06-18"
STATELESS_PROTOCOL_VERSION: Final = "2026-07-28"
CLIENT_INFO: Json = {"name": "mcp-access", "version": "1.0.0"}

EXIT_OK: Final = 0
EXIT_OP_FAILED: Final = 1
EXIT_TRANSPORT: Final = 2


@dataclass(frozen=True)
class ListOp:
    """tools/list: list every tool."""


@dataclass(frozen=True)
class CallOp:
    """tools/call: run one tool."""

    tool: str
    arguments: Json | None


@dataclass(frozen=True)
class RawOp:
    """Any other JSON-RPC request."""

    method: str
    params: Json | None


Op: TypeAlias = ListOp | CallOp | RawOp


class ByteStream(Protocol):
    """Anything with the single-byte read HTTPResponse provides."""

    def read(self, amt: int) -> bytes: ...


class Transport(Protocol):
    """Exchanges JSON-RPC messages with one MCP server."""

    def request(self, msg: Json, extra_headers: HeaderList, deadline: float) -> Json:
        """Send a request and return its matching response."""
        ...

    def notify(self, msg: Json, extra_headers: HeaderList, deadline: float) -> None:
        """Send a notification; no response is expected."""
        ...

    def stop(self) -> None:
        """Tear the connection down."""
        ...


class NeedsStatelessError(Exception):
    """Raised when an HTTP server's 400 response demands stateless-era headers."""


def log(message: str) -> None:
    print(f"[mcp] {message}", file=sys.stderr, flush=True)


def fail(code: int, message: str) -> NoReturn:
    log(f"error: {message}")
    sys.exit(code)


def parse_json_object(text: str, what: str) -> Json:
    try:
        parsed = json.loads(text)
    except ValueError as exc:
        fail(EXIT_TRANSPORT, f"invalid JSON for {what}: {exc}; got: {text[:200]}")
    if not isinstance(parsed, dict):
        fail(EXIT_TRANSPORT, f"JSON for {what} must be an object, got: {text[:200]}")
    return cast(Json, parsed)


def parse_ops(words: Sequence[str]) -> list[Op]:
    """Parse the op list: list | call TOOL [ARGS] | raw METHOD [PARAMS], repeatable."""
    ops: list[Op] = []
    i = 0
    while i < len(words):
        word = words[i]
        if word == "list":
            ops.append(ListOp())
            i += 1
            continue
        if word == "call":
            if i + 1 >= len(words):
                fail(EXIT_TRANSPORT, "op 'call' needs a tool name: call <tool> ['<json-arguments>']")
            tool = words[i + 1]
            arguments: Json | None = None
            if i + 2 < len(words) and words[i + 2].startswith("{"):
                arguments = parse_json_object(words[i + 2], f"arguments of tool {tool!r}")
                i += 1
            elif i + 2 < len(words) and words[i + 2] not in ("list", "call", "raw"):
                fail(EXIT_TRANSPORT, f"arguments for 'call {tool}' must be a single JSON object (starting with '{{'); got {words[i + 2]!r}")
            ops.append(CallOp(tool=tool, arguments=arguments))
            i += 2
            continue
        if word == "raw":
            if i + 1 >= len(words):
                fail(EXIT_TRANSPORT, "op 'raw' needs a method name: raw <method> ['<json-params>']")
            method = words[i + 1]
            params: Json | None = None
            if i + 2 < len(words) and words[i + 2].startswith("{"):
                params = parse_json_object(words[i + 2], f"params of method {method!r}")
                i += 1
            ops.append(RawOp(method=method, params=params))
            i += 2
            continue
        fail(EXIT_TRANSPORT, f"unknown operation {word!r}; expected 'list', 'call <tool> [args]', or 'raw <method> [params]'")
    return ops


class StdioTransport:
    """Spawn a stdio MCP server and speak newline-delimited JSON-RPC with it."""

    def __init__(self, command: str, verbose: bool) -> None:
        self.command = command
        self.verbose = verbose
        self.buf = b""
        self.lines: list[bytes] = []
        argv = shlex.split(command)
        if not argv:
            fail(EXIT_TRANSPORT, "--cmd is empty; pass the server command, e.g. --cmd 'npx -y chrome-devtools-mcp@latest'")
        try:
            proc = subprocess.Popen(
                argv,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=None,
                start_new_session=True,
            )
        except OSError as exc:
            fail(EXIT_TRANSPORT, f"cannot run {command!r}: {exc}")
        assert proc.stdin is not None and proc.stdout is not None
        self.proc = proc
        self.stdin = proc.stdin
        self.stdout = proc.stdout

    def stop(self) -> None:
        try:
            self.stdin.close()
        except OSError:
            pass
        try:
            self.proc.wait(timeout=5)
            return
        except subprocess.TimeoutExpired:
            pass
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(os.getpgid(self.proc.pid), sig)
            except OSError:
                try:
                    self.proc.send_signal(sig)
                except OSError:
                    pass
            try:
                self.proc.wait(timeout=5)
                return
            except subprocess.TimeoutExpired:
                continue

    def _send(self, msg: Json) -> None:
        if self.verbose:
            log(f"-> {json.dumps(msg)[:500]}")
        try:
            self.stdin.write((json.dumps(msg, separators=(",", ":")) + "\n").encode("utf-8"))
            self.stdin.flush()
        except (BrokenPipeError, OSError):
            fail(EXIT_TRANSPORT, f"the server for {self.command!r} closed its stdin; run that command alone to see its startup errors")

    def _next_message(self, deadline: float) -> Json | None:
        """Return the next JSON object from stdout, or None when the server is gone."""
        while True:
            while self.lines:
                line = self.lines.pop(0)
                text = line.decode("utf-8", "replace").strip()
                if not text:
                    continue
                try:
                    msg = json.loads(text)
                except ValueError:
                    log(f"server wrote a non-JSON line to stdout (ignored): {text[:200]}")
                    continue
                if isinstance(msg, dict):
                    if self.verbose:
                        log(f"<- {json.dumps(msg)[:500]}")
                    return cast(Json, msg)
                log(f"server wrote a non-object line to stdout (ignored): {text[:200]}")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("timed out waiting for the server to respond")
            try:
                ready, _, _ = select.select([self.stdout], [], [], remaining)
            except InterruptedError:
                continue
            if not ready:
                continue
            chunk = os.read(self.stdout.fileno(), 65536)
            if not chunk:
                return None
            self.buf += chunk
            while b"\n" in self.buf:
                raw, self.buf = self.buf.split(b"\n", 1)
                self.lines.append(raw)

    def request(self, msg: Json, extra_headers: HeaderList, deadline: float) -> Json:
        self._send(msg)
        want_id = msg["id"]
        while True:
            other = self._next_message(deadline)
            if other is None:
                fail(EXIT_TRANSPORT, f"the server for {self.command!r} exited before responding; run that command alone to see its startup errors")
            if "method" not in other:
                if other.get("id") == want_id and ("result" in other or "error" in other):
                    return other
                log(f"ignoring a response with unknown id {other.get('id')!r}")
                continue
            if "id" not in other:
                log(f"server notification: {other.get('method')}")
                continue
            method = other.get("method")
            if method == "ping":
                reply: Json = {"jsonrpc": "2.0", "id": other["id"], "result": {}}
                note = "answered ping with an empty result"
            else:
                reply = {"jsonrpc": "2.0", "id": other["id"], "error": {"code": -32601, "message": "method not supported by the mcp-access script"}}
                note = "replied method-not-found so the server does not block"
            self._send(reply)
            log(f"server sent a {method!r} request; {note}")

    def notify(self, msg: Json, extra_headers: HeaderList, deadline: float) -> None:
        self._send(msg)


class HttpTransport:
    """POST JSON-RPC messages to a streamable HTTP MCP endpoint."""

    def __init__(self, url: str, headers: Iterable[str], verbose: bool) -> None:
        self.url = url
        self.verbose = verbose
        self.session_id: str | None = None
        self.base_headers: list[tuple[str, str]] = []
        for item in headers:
            if ":" not in item:
                fail(EXIT_TRANSPORT, f"--header must be 'Name: Value'; got {item!r}")
            name, value = item.split(":", 1)
            self.base_headers.append((name.strip(), value.strip()))

    def stop(self) -> None:
        # Nothing to tear down: each request opens its own connection.
        pass

    def _post(self, msg: Json, extra_headers: HeaderList, deadline: float) -> HTTPResponse:
        """POST one message and return the open 2xx response."""
        body = json.dumps(msg, separators=(",", ":")).encode("utf-8")
        req = urllib.request.Request(self.url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json, text/event-stream")
        for name, value in self.base_headers:
            req.add_header(name, value)
        for name, value in extra_headers:
            req.add_header(name, value)
        if self.session_id:
            req.add_header("Mcp-Session-Id", self.session_id)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("timed out before sending the request")
        if self.verbose:
            log(f"-> POST {self.url} {msg.get('method')}")
        try:
            return cast(HTTPResponse, urllib.request.urlopen(req, timeout=remaining))
        except urllib.error.HTTPError as exc:
            self._http_error(exc)
        except urllib.error.URLError as exc:
            reason = exc.reason
            if isinstance(reason, (socket.timeout, TimeoutError)):
                fail(EXIT_TRANSPORT, f"timed out talking to {self.url}; increase --timeout")
            fail(EXIT_TRANSPORT, f"cannot reach {self.url}: {reason}; check the host, port, and that the server is running")
        except (socket.timeout, TimeoutError):
            fail(EXIT_TRANSPORT, f"timed out talking to {self.url}; increase --timeout")

    def request(self, msg: Json, extra_headers: HeaderList, deadline: float) -> Json:
        with self._post(msg, extra_headers, deadline) as resp:
            status = resp.status
            session = resp.headers.get("Mcp-Session-Id")
            if session:
                self.session_id = session
            if status != 200:
                fail(EXIT_TRANSPORT, f"server returned HTTP {status} (expected 200) for a request; the endpoint may not be a streamable HTTP MCP endpoint, or the server wants the stateless 2026-07-28 protocol")
            content_type = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            if content_type == "text/event-stream":
                return self._read_sse_response(resp, msg["id"], deadline)
            raw = resp.read()
        if self.verbose:
            log(f"<- HTTP {status} {content_type} ({len(raw)} bytes)")
        return self._parse_response(raw, content_type, msg["id"])

    def notify(self, msg: Json, extra_headers: HeaderList, deadline: float) -> None:
        with self._post(msg, extra_headers, deadline) as resp:
            session = resp.headers.get("Mcp-Session-Id")
            if session:
                self.session_id = session
            # Any 2xx is accepted; the body is not read, since a server may
            # hold the response stream open after accepting a notification.

    def _http_error(self, exc: urllib.error.HTTPError) -> NoReturn:
        code = exc.code
        try:
            body = exc.read().decode("utf-8", "replace")
        except Exception:
            body = ""
        if code == 400 and ("HeaderMismatch" in body or "-32020" in body):
            raise NeedsStatelessError(body)
        hint = ""
        if code in (401, 403):
            hint = "; the endpoint requires authentication: pass --header 'Authorization: Bearer <token>' (or the auth the server's docs specify)"
        elif code == 404:
            hint = "; wrong URL path or the session expired mid-run. If this is an SSE endpoint (e.g. ending in /sse), it cannot be POSTed to directly: use the MCP Inspector with --transport sse"
        elif code == 405:
            hint = "; this endpoint may be SSE-only or expects different HTTP methods. If it is SSE, use the MCP Inspector with --transport sse"
        fail(EXIT_TRANSPORT, f"HTTP {code} from {self.url}: {body[:300] or '(empty body)'}{hint}")

    def _read_sse_response(self, resp: ByteStream, want_id: int, deadline: float) -> Json:
        """Return the reply from an SSE response body, reading line by line.

        A server may keep the response stream open after sending the reply,
        so this returns as soon as the id-matched message arrives instead
        of reading to EOF.
        """
        lines: list[str] = []

        def dispatch() -> Json | None:
            candidate = self._sse_message("\n".join(lines))
            if candidate is None:
                return None
            if candidate.get("id") == want_id and ("result" in candidate or "error" in candidate):
                return candidate
            log(f"ignoring a server message while waiting for the reply: {json.dumps(candidate)[:200]}")
            return None

        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("timed out waiting for the SSE response")
            line = self._readline(resp)
            if not line:
                break
            text = line.decode("utf-8", "replace").rstrip("\r\n")
            if text:
                lines.append(text)
                continue
            found = dispatch()
            lines = []
            if found is not None:
                if self.verbose:
                    log(f"<- HTTP 200 text/event-stream (reply for id {want_id})")
                return found
        found = dispatch()  # a server may end the last event without a blank line
        if found is not None:
            return found
        fail(EXIT_TRANSPORT, "the server closed the SSE response before sending a reply")

    @staticmethod
    def _readline(resp: ByteStream) -> bytes:
        """Read one newline-terminated line, one byte at a time.

        Larger reads block until they fill or the stream closes, which
        stalls against servers that keep the SSE response open after the
        reply; single-byte reads return as data arrives.
        """
        line = bytearray()
        while True:
            byte = resp.read(1)
            if not byte:
                return bytes(line)
            line += byte
            if byte == b"\n":
                return bytes(line)

    @staticmethod
    def _sse_message(block_text: str) -> Json | None:
        data = [line[5:].strip() for line in block_text.splitlines() if line.startswith("data:")]
        if not data:
            return None
        try:
            parsed = json.loads("\n".join(data))
        except ValueError:
            return None
        if isinstance(parsed, dict):
            return cast(Json, parsed)
        return None

    def _parse_response(self, raw: bytes, content_type: str, want_id: int) -> Json:
        text = raw.decode("utf-8", "replace")
        try:
            candidate = json.loads(text)
        except ValueError:
            fail(EXIT_TRANSPORT, f"response is not JSON (Content-Type {content_type!r}): {text[:300]}")
        if isinstance(candidate, dict) and candidate.get("id") == want_id:
            return cast(Json, candidate)
        fail(EXIT_TRANSPORT, f"no response with id {want_id!r} in the server reply: {text[:300]}")


class Client:
    """MCP protocol logic on top of a transport: handshake, stateless mode, ops."""

    def __init__(self, transport: Transport, timeout: float, proposed: str) -> None:
        self.transport = transport
        self.timeout = timeout
        self.proposed = proposed
        self.negotiated: str | None = None
        self.stateless = False
        self.next_id = 1

    def _id(self) -> int:
        value = self.next_id
        self.next_id += 1
        return value

    def _headers(self, method: str, params: Json | None) -> list[tuple[str, str]]:
        headers: list[tuple[str, str]] = []
        if self.stateless:
            assert self.negotiated is not None  # set by _switch_stateless or the handshake
            headers.append(("MCP-Protocol-Version", self.negotiated))
            headers.append(("Mcp-Method", method))
            name = (params.get("name") or params.get("uri")) if isinstance(params, dict) else None
            if name is not None:
                headers.append(("Mcp-Name", str(name)))
        elif self.negotiated:
            headers.append(("MCP-Protocol-Version", self.negotiated))
        return headers

    def _request(self, method: str, params: Json | None) -> Json:
        msg: Json = {"jsonrpc": "2.0", "id": self._id(), "method": method}
        if params is not None:
            msg["params"] = params
        deadline = time.monotonic() + self.timeout
        return self.transport.request(msg, self._headers(method, params), deadline)

    def _notify(self, method: str) -> None:
        msg: Json = {"jsonrpc": "2.0", "method": method}
        deadline = time.monotonic() + self.timeout
        self.transport.notify(msg, self._headers(method, None), deadline)

    def connect(self) -> None:
        try:
            self._connect_with_handshake()
        except NeedsStatelessError:
            self._switch_stateless(
                STATELESS_PROTOCOL_VERSION,
                "server rejected the handshake with a header-mismatch error",
            )

    def _connect_with_handshake(self) -> None:
        tried: list[str] = []
        version = self.proposed
        while True:
            tried.append(version)
            params: Json = {"protocolVersion": version, "capabilities": {}, "clientInfo": CLIENT_INFO}
            resp = self._request("initialize", params)
            if "error" not in resp:
                result = resp.get("result") or {}
                self.negotiated = result.get("protocolVersion") or version
                server = result.get("serverInfo") or {}
                log(f"connected: {server.get('name', 'unknown server')} {server.get('version', '')} (protocol {self.negotiated})")
                self._notify("notifications/initialized")
                return
            error = resp["error"]
            data = error.get("data") if isinstance(error.get("data"), dict) else {}
            supported = data.get("supported") or []
            if error.get("code") == -32601:
                self._switch_stateless(STATELESS_PROTOCOL_VERSION, "server has no initialize method")
                return
            if error.get("code") in (-32022, -32602) and supported:
                older = [v for v in supported if v < STATELESS_PROTOCOL_VERSION and v not in tried]
                if older:
                    version = max(older)
                    log(f"server rejected protocol {tried[-1]!r}; retrying initialize with {version!r}")
                    continue
                self._switch_stateless(max(supported), "server only supports stateless-era protocol versions")
                return
            fail(EXIT_TRANSPORT, f"initialize failed: {json.dumps(error)}")

    def _switch_stateless(self, version: str, why: str) -> None:
        self.stateless = True
        self.negotiated = version
        log(f"{why}; switching to stateless mode (protocol {version}: per-request _meta and Mcp-Method/Mcp-Name headers)")

    def _with_meta(self, params: Json | None) -> Json | None:
        if not self.stateless:
            return params
        params = dict(params or {})
        params["_meta"] = {
            "io.modelcontextprotocol/protocolVersion": self.negotiated,
            "io.modelcontextprotocol/clientCapabilities": {},
            "io.modelcontextprotocol/clientInfo": CLIENT_INFO,
        }
        return params

    def run(self, ops: Sequence[Op]) -> None:
        for op in ops:
            if isinstance(op, ListOp):
                self._tools_list()
            elif isinstance(op, CallOp):
                self._tools_call(op.tool, op.arguments)
            else:
                self._raw(op.method, op.params)

    def _tools_list(self) -> None:
        tools: list[Json] = []
        cursor = None
        while True:
            params: Json = {"cursor": cursor} if cursor else {}
            resp = self._request("tools/list", self._with_meta(params))
            if "error" in resp:
                print(json.dumps(resp, indent=2))
                fail(EXIT_OP_FAILED, "tools/list returned a protocol error (the server may have no tools capability)")
            result = resp.get("result") or {}
            tools.extend(result.get("tools") or [])
            cursor = result.get("nextCursor")
            if not cursor:
                break
        print(json.dumps({"tools": tools}, indent=2))
        log(f"{len(tools)} tools")

    def _tools_call(self, tool: str, arguments: Json | None) -> None:
        params: Json = {"name": tool}
        if arguments is not None:
            params["arguments"] = arguments
        log(f"calling tool {tool!r}")
        resp = self._request("tools/call", self._with_meta(params))
        if "error" in resp:
            print(json.dumps(resp, indent=2))
            fail(EXIT_OP_FAILED, "tools/call returned a protocol error: unknown tool, invalid arguments, or no tools capability; run 'list' and check the tool's inputSchema")
        result = resp.get("result") or {}
        print(json.dumps(result, indent=2))
        if result.get("isError"):
            fail(EXIT_OP_FAILED, "the tool executed and reported isError=true; see the content above for its error message")

    def _raw(self, method: str, params: Json | None) -> None:
        resp = self._request(method, self._with_meta(params))
        print(json.dumps(resp, indent=2))
        if "error" in resp:
            fail(EXIT_OP_FAILED, f"{method} returned an error response")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mcp_call.py",
        description="Call an MCP server without an MCP host: list tools and call them over stdio or streamable HTTP.",
    )
    sub = parser.add_subparsers(dest="mode", required=True)

    stdio = sub.add_parser("stdio", help="spawn a stdio MCP server command and talk JSON-RPC over stdin/stdout")
    stdio.add_argument("--cmd", required=True, metavar="COMMAND",
                       help="server command line, e.g. --cmd 'npx -y chrome-devtools-mcp@latest'")
    _add_common(stdio)
    stdio.add_argument("ops", nargs="+", metavar="op",
                       help="list | call TOOL ['<json-args>'] | raw METHOD ['<json-params>']; repeatable, runs in order")

    http = sub.add_parser("http", help="POST JSON-RPC to a streamable HTTP MCP endpoint")
    http.add_argument("url", help="endpoint URL, e.g. http://localhost:8083/mcp")
    http.add_argument("--header", action="append", default=[], metavar="NAME: VALUE",
                      help="extra HTTP header, repeatable, e.g. --header 'Authorization: Bearer TOKEN'")
    _add_common(http)
    http.add_argument("ops", nargs="+", metavar="op",
                      help="list | call TOOL ['<json-args>'] | raw METHOD ['<json-params>']; repeatable, runs in order")
    return parser


def _add_common(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("--timeout", type=float, default=300.0, metavar="SECS",
                     help="seconds to wait for each response (default: 300)")
    sub.add_argument("--protocol-version", default=DEFAULT_PROTOCOL_VERSION, metavar="VERSION",
                     help=f"protocol version proposed during initialize (default: {DEFAULT_PROTOCOL_VERSION})")
    sub.add_argument("--verbose", action="store_true", help="log every protocol message to stderr")


def main() -> None:
    args = build_parser().parse_args()
    ops = parse_ops(args.ops)
    if args.mode == "stdio":
        transport: Transport = StdioTransport(args.cmd, args.verbose)
    else:
        transport = HttpTransport(args.url, args.header, args.verbose)
    client = Client(transport, timeout=args.timeout, proposed=args.protocol_version)
    exit_code = EXIT_OK
    try:
        client.connect()
        client.run(ops)
    except (TimeoutError, socket.timeout) as exc:
        fail(EXIT_TRANSPORT, f"{exc}; increase --timeout (currently {args.timeout:g}s) if the server is slow to start (JVM startup, browser launch, indexing)")
    except KeyboardInterrupt:
        log("interrupted; shutting the server down")
        exit_code = 130
    except NeedsStatelessError as exc:
        fail(EXIT_TRANSPORT, f"server rejected request headers: {str(exc)[:200]}")
    except Exception as exc:
        fail(EXIT_TRANSPORT, f"unexpected {type(exc).__name__}: {exc}")
    finally:
        transport.stop()
    sys.exit(exit_code)


def run_tests() -> None:
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(EXIT_OK if result.wasSuccessful() else 1)


# --- built-in tests: run with `mcp_call.py --self-test` -----------------------


class FakeTransport:
    """Canned JSON-RPC responses for Client tests; records every message sent."""

    def __init__(self, responses: Sequence[Json]) -> None:
        self.responses = list(responses)
        self.requests: list[Json] = []
        self.notifications: list[Json] = []
        self.headers: list[HeaderList] = []

    def request(self, msg: Json, extra_headers: HeaderList, deadline: float) -> Json:
        self.requests.append(msg)
        self.headers.append(extra_headers)
        return self.responses.pop(0)

    def notify(self, msg: Json, extra_headers: HeaderList, deadline: float) -> None:
        self.notifications.append(msg)

    def stop(self) -> None:
        pass


class FakeBody:
    """A byte source with the read(amt) interface the SSE reader needs."""

    def __init__(self, data: bytes) -> None:
        self.data = data

    def read(self, amt: int) -> bytes:
        chunk, self.data = self.data[:amt], self.data[amt:]
        return chunk


def make_client(responses: Sequence[Json]) -> tuple[Client, FakeTransport]:
    transport = FakeTransport(responses)
    return Client(transport, timeout=5.0, proposed="2025-06-18"), transport


def init_result(version: str = "2025-06-18") -> Json:
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "protocolVersion": version,
            "capabilities": {},
            "serverInfo": {"name": "fake", "version": "0"},
        },
    }


def error_result(code: int, supported: Sequence[str] | None = None) -> Json:
    error: Json = {"code": code, "message": "canned error"}
    if supported is not None:
        error["data"] = {"supported": list(supported)}
    return {"jsonrpc": "2.0", "id": 1, "error": error}


class ParseOpsTest(unittest.TestCase):
    def test_list_call_raw_sequence(self) -> None:
        ops = parse_ops(["list", "call", "echo", '{"message":"hi"}', "raw", "resources/list", "call", "ping"])
        self.assertEqual(ops, [
            ListOp(),
            CallOp(tool="echo", arguments={"message": "hi"}),
            RawOp(method="resources/list", params=None),
            CallOp(tool="ping", arguments=None),
        ])

    def test_bare_op_word_after_tool_name_starts_next_op(self) -> None:
        self.assertEqual(parse_ops(["call", "echo", "list"]),
                         [CallOp(tool="echo", arguments=None), ListOp()])

    def test_bad_input_exits(self) -> None:
        for words in (["bogus"], ["call"], ["call", "echo", "notjson"],
                      ["call", "echo", "{"], ["raw"]):
            with self.subTest(words=words):
                with self.assertRaises(SystemExit) as ctx:
                    with contextlib.redirect_stderr(io.StringIO()):
                        parse_ops(words)
                self.assertEqual(ctx.exception.code, EXIT_TRANSPORT)


class ClientHandshakeTest(unittest.TestCase):
    def test_connect_uses_server_version_and_notifies(self) -> None:
        client, transport = make_client([init_result("2025-11-25")])
        client.connect()
        self.assertFalse(client.stateless)
        self.assertEqual(client.negotiated, "2025-11-25")
        self.assertEqual(transport.notifications[0]["method"], "notifications/initialized")
        self.assertEqual(client._headers("tools/list", None), [("MCP-Protocol-Version", "2025-11-25")])

    def test_retry_on_unsupported_version_error(self) -> None:
        for code in (-32022, -32602):
            with self.subTest(code=code):
                client, transport = make_client([
                    error_result(code, supported=["2024-11-05", "2026-07-28"]),
                    init_result("2024-11-05"),
                ])
                client.connect()
                self.assertEqual(client.negotiated, "2024-11-05")
                self.assertEqual(transport.requests[1]["params"]["protocolVersion"], "2024-11-05")

    def test_stateless_switch_on_missing_initialize(self) -> None:
        client, transport = make_client([
            error_result(-32601),
            {"jsonrpc": "2.0", "id": 2, "result": {"content": [{"type": "text", "text": "Echo: hi"}], "resultType": "complete"}},
        ])
        client.connect()
        self.assertTrue(client.stateless)
        client.run([CallOp(tool="echo", arguments={"message": "hi"})])
        call = transport.requests[1]
        self.assertEqual(call["params"]["_meta"]["io.modelcontextprotocol/protocolVersion"], "2026-07-28")
        self.assertEqual(transport.headers[1], [
            ("MCP-Protocol-Version", "2026-07-28"),
            ("Mcp-Method", "tools/call"),
            ("Mcp-Name", "echo"),
        ])

    def test_with_meta_passthrough_and_injection(self) -> None:
        client, _ = make_client([])
        params: Json = {"name": "echo"}
        self.assertEqual(client._with_meta(params), params)
        client._switch_stateless("2026-07-28", "test")
        with_meta = client._with_meta(params)
        assert with_meta is not None
        self.assertEqual(with_meta["name"], "echo")
        self.assertEqual(with_meta["_meta"]["io.modelcontextprotocol/protocolVersion"], "2026-07-28")


class ClientOpsTest(unittest.TestCase):
    def test_tools_list_merges_pages(self) -> None:
        client, transport = make_client([
            init_result(),
            {"jsonrpc": "2.0", "id": 2, "result": {"tools": [{"name": "a"}], "nextCursor": "page2"}},
            {"jsonrpc": "2.0", "id": 3, "result": {"tools": [{"name": "b"}]}},
        ])
        client.connect()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            client.run([ListOp()])
        self.assertEqual(transport.requests[2]["params"], {"cursor": "page2"})
        self.assertIn('"name": "a"', out.getvalue())
        self.assertIn('"name": "b"', out.getvalue())

    def test_tools_call_reports_tool_error(self) -> None:
        client, _ = make_client([
            init_result(),
            {"jsonrpc": "2.0", "id": 2, "result": {"content": [{"type": "text", "text": "boom"}], "isError": True}},
        ])
        client.connect()
        with self.assertRaises(SystemExit) as ctx:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                client.run([CallOp(tool="echo", arguments={})])
        self.assertEqual(ctx.exception.code, EXIT_OP_FAILED)

    def test_raw_prints_error_and_exits(self) -> None:
        client, _ = make_client([init_result(), error_result(-32602)])
        client.connect()
        with self.assertRaises(SystemExit) as ctx:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                client.run([RawOp(method="resources/list", params=None)])
        self.assertEqual(ctx.exception.code, EXIT_OP_FAILED)


class ReadlineTest(unittest.TestCase):
    def test_newline_terminated(self) -> None:
        self.assertEqual(HttpTransport._readline(FakeBody(b"ab\ncd\n")), b"ab\n")

    def test_eof_mid_line_returns_partial(self) -> None:
        self.assertEqual(HttpTransport._readline(FakeBody(b"ab")), b"ab")


class SseMessageTest(unittest.TestCase):
    def test_extracts_data_lines(self) -> None:
        block = 'event: message\nid: abc\ndata: {"jsonrpc":"2.0","id":1,"result":{}}'
        msg = HttpTransport._sse_message(block)
        assert msg is not None
        self.assertEqual(msg["id"], 1)

    def test_multiline_data_joined(self) -> None:
        msg = HttpTransport._sse_message('data: {"a":\ndata: 1}')
        assert msg is not None
        self.assertEqual(msg, {"a": 1})

    def test_no_data_or_bad_json_returns_none(self) -> None:
        self.assertIsNone(HttpTransport._sse_message(": comment\n"))
        self.assertIsNone(HttpTransport._sse_message("data: not-json"))
        self.assertIsNone(HttpTransport._sse_message("data: 42"))


class SseResponseTest(unittest.TestCase):
    def setUp(self) -> None:
        self.transport = HttpTransport("http://localhost/mcp", [], verbose=False)
        self.deadline = time.monotonic() + 5.0

    def test_returns_matching_reply_among_notifications(self) -> None:
        body = (
            'event: message\ndata: {"jsonrpc":"2.0","method":"notifications/progress"}\n\n'
            ": keep-alive comment\n\n"
            'event: message\ndata: {"jsonrpc":"2.0","id":7,"result":{"content":[]}}\n\n'
        ).encode()
        reply = self.transport._read_sse_response(FakeBody(body), 7, self.deadline)
        self.assertEqual(reply["id"], 7)

    def test_crlf_events(self) -> None:
        body = 'event: message\r\ndata: {"jsonrpc":"2.0","id":1,"result":{}}\r\n\r\n'.encode()
        reply = self.transport._read_sse_response(FakeBody(body), 1, self.deadline)
        self.assertEqual(reply["result"], {})

    def test_reply_without_trailing_blank_line(self) -> None:
        body = 'data: {"jsonrpc":"2.0","id":1,"error":{"code":-1}}'.encode()
        reply = self.transport._read_sse_response(FakeBody(body), 1, self.deadline)
        self.assertIn("error", reply)

    def test_closed_without_reply_exits(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            with contextlib.redirect_stderr(io.StringIO()):
                self.transport._read_sse_response(FakeBody(b": comment\n\n"), 5, self.deadline)
        self.assertEqual(ctx.exception.code, EXIT_TRANSPORT)


class ParseResponseTest(unittest.TestCase):
    def setUp(self) -> None:
        self.transport = HttpTransport("http://localhost/mcp", [], verbose=False)

    def test_matching_id(self) -> None:
        resp = self.transport._parse_response(b'{"jsonrpc":"2.0","id":3,"result":{}}', "application/json", 3)
        self.assertEqual(resp["result"], {})

    def test_wrong_id_exits(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            with contextlib.redirect_stderr(io.StringIO()):
                self.transport._parse_response(b'{"jsonrpc":"2.0","id":9,"result":{}}', "application/json", 3)
        self.assertEqual(ctx.exception.code, EXIT_TRANSPORT)

    def test_not_json_exits(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            with contextlib.redirect_stderr(io.StringIO()):
                self.transport._parse_response(b"<html/>", "text/html", 3)
        self.assertEqual(ctx.exception.code, EXIT_TRANSPORT)


class HeaderParsingTest(unittest.TestCase):
    def test_rejects_header_without_colon(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            with contextlib.redirect_stderr(io.StringIO()):
                HttpTransport("http://localhost/mcp", ["BadHeader"], verbose=False)
        self.assertEqual(ctx.exception.code, EXIT_TRANSPORT)


class StatelessStdioIntegrationTest(unittest.TestCase):
    """End to end against the sibling mock server (offline, no network)."""

    def test_switch_and_echo(self) -> None:
        mock = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mock_stateless_server.py")
        transport: Transport = StdioTransport(f"{sys.executable} {mock}", verbose=False)
        client = Client(transport, timeout=30.0, proposed="2025-06-18")
        try:
            client.connect()
            self.assertTrue(client.stateless)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                client.run([ListOp(), CallOp(tool="echo", arguments={"message": "self-test"})])
        finally:
            transport.stop()
        self.assertIn('"name": "echo"', out.getvalue())
        self.assertIn("Echo: self-test", out.getvalue())


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        run_tests()
    else:
        main()
