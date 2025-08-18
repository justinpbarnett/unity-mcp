import sys
import json
import struct
import socket
import threading
import time
import select
from pathlib import Path

import pytest

# locate server src dynamically to avoid hardcoded layout assumptions
ROOT = Path(__file__).resolve().parents[1]
candidates = [
    ROOT / "UnityMcpBridge" / "UnityMcpServer~" / "src",
    ROOT / "UnityMcpServer~" / "src",
]
SRC = next((p for p in candidates if p.exists()), None)
if SRC is None:
    searched = "\n".join(str(p) for p in candidates)
    pytest.skip(
        "Unity MCP server source not found. Tried:\n" + searched,
        allow_module_level=True,
    )
sys.path.insert(0, str(SRC))

from unity_connection import UnityConnection


def start_dummy_server(greeting: bytes, respond_ping: bool = False):
    """Start a minimal TCP server for handshake tests."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    sock.listen(1)
    port = sock.getsockname()[1]
    ready = threading.Event()

    def _run():
        ready.set()
        conn, _ = sock.accept()
        conn.settimeout(1.0)
        if greeting:
            conn.sendall(greeting)
        if respond_ping:
            try:
                # Read exactly n bytes helper
                def _read_exact(n: int) -> bytes:
                    buf = b""
                    while len(buf) < n:
                        chunk = conn.recv(n - len(buf))
                        if not chunk:
                            break
                        buf += chunk
                    return buf

                header = _read_exact(8)
                if len(header) == 8:
                    length = struct.unpack(">Q", header)[0]
                    payload = _read_exact(length)
                    if payload == b'{"type":"ping"}':
                        resp = b'{"type":"pong"}'
                        conn.sendall(struct.pack(">Q", len(resp)) + resp)
            except Exception:
                pass
        time.sleep(0.1)
        try:
            conn.close()
        except Exception:
            pass
        finally:
            sock.close()

    threading.Thread(target=_run, daemon=True).start()
    ready.wait()
    return port


def start_handshake_enforcing_server():
    """Server that drops connection if client sends data before handshake."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    sock.listen(1)
    port = sock.getsockname()[1]
    ready = threading.Event()

    def _run():
        ready.set()
        conn, _ = sock.accept()
        # If client sends any data before greeting, disconnect (poll briefly)
        deadline = time.time() + 0.5
        while time.time() < deadline:
            r, _, _ = select.select([conn], [], [], 0.05)
            if r:
                conn.close()
                sock.close()
                return
        conn.sendall(b"MCP/0.1 FRAMING=1\n")
        time.sleep(0.1)
        conn.close()
        sock.close()

    threading.Thread(target=_run, daemon=True).start()
    ready.wait()
    return port


def test_handshake_requires_framing():
    port = start_dummy_server(b"MCP/0.1\n")
    conn = UnityConnection(host="127.0.0.1", port=port)
    assert conn.connect() is False
    assert conn.sock is None


def test_small_frame_ping_pong():
    port = start_dummy_server(b"MCP/0.1 FRAMING=1\n", respond_ping=True)
    conn = UnityConnection(host="127.0.0.1", port=port)
    try:
        assert conn.connect() is True
        assert conn.use_framing is True
        payload = b'{"type":"ping"}'
        conn.sock.sendall(struct.pack(">Q", len(payload)) + payload)
        resp = conn.receive_full_response(conn.sock)
        assert json.loads(resp.decode("utf-8"))["type"] == "pong"
    finally:
        conn.disconnect()


def test_unframed_data_disconnect():
    port = start_handshake_enforcing_server()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(("127.0.0.1", port))
    sock.sendall(b"BAD")
    time.sleep(0.4)
    try:
        data = sock.recv(1024)
        assert data == b""
    except (ConnectionResetError, ConnectionAbortedError):
        # Some platforms raise instead of returning empty bytes when the
        # server closes the connection after detecting pre-handshake data.
        pass
    finally:
        sock.close()


@pytest.mark.skip(reason="TODO: zero-length payload should raise error")
def test_zero_length_payload_error():
    pass


@pytest.mark.skip(reason="TODO: oversized payload should disconnect")
def test_oversized_payload_rejected():
    pass


@pytest.mark.skip(reason="TODO: partial header/payload triggers timeout and disconnect")
def test_partial_frame_timeout():
    pass


@pytest.mark.skip(reason="TODO: concurrency test with parallel tool invocations")
def test_parallel_invocations_no_interleaving():
    pass


@pytest.mark.skip(reason="TODO: reconnection after drop mid-command")
def test_reconnect_mid_command():
    pass
