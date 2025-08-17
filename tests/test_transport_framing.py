import sys
import json
import struct
import socket
import threading
import time
from pathlib import Path

import pytest

# add server src to path
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "UnityMcpBridge" / "UnityMcpServer~" / "src"
sys.path.insert(0, str(SRC))

from unity_connection import UnityConnection


def start_dummy_server(greeting: bytes, respond_ping: bool = False):
    """Start a minimal TCP server for handshake tests."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    sock.listen(1)
    port = sock.getsockname()[1]

    def _run():
        conn, _ = sock.accept()
        if greeting:
            conn.sendall(greeting)
        if respond_ping:
            try:
                header = conn.recv(8)
                if len(header) == 8:
                    length = struct.unpack(">Q", header)[0]
                    payload = b""
                    while len(payload) < length:
                        chunk = conn.recv(length - len(payload))
                        if not chunk:
                            break
                        payload += chunk
                    if payload == b'{"type":"ping"}':
                        resp = b'{"type":"pong"}'
                        conn.sendall(struct.pack(">Q", len(resp)) + resp)
            except Exception:
                pass
        time.sleep(0.1)
        try:
            conn.close()
        finally:
            sock.close()

    threading.Thread(target=_run, daemon=True).start()
    return port


def test_handshake_requires_framing():
    port = start_dummy_server(b"MCP/0.1\n")
    conn = UnityConnection(host="127.0.0.1", port=port)
    assert conn.connect() is False
    assert conn.sock is None


def test_small_frame_ping_pong():
    port = start_dummy_server(b"MCP/0.1 FRAMING=1\n", respond_ping=True)
    conn = UnityConnection(host="127.0.0.1", port=port)
    assert conn.connect() is True
    assert conn.use_framing is True
    payload = b'{"type":"ping"}'
    conn.sock.sendall(struct.pack(">Q", len(payload)) + payload)
    resp = conn.receive_full_response(conn.sock)
    assert json.loads(resp.decode("utf-8"))["type"] == "pong"
    conn.disconnect()


@pytest.mark.skip(reason="TODO: unframed data before reading greeting should disconnect")
def test_unframed_data_disconnect():
    pass


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
