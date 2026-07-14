"""
Support helpers for the submission test scripts.

Responsibilities:
1. Allow scripts under submission_package/03_test_scripts to run directly.
2. Share the TCP framing helpers used by the project protocol.
"""
import json
import socket
import sys
from pathlib import Path


TEST_DIR = Path(__file__).resolve().parent
SUBMISSION_ROOT = TEST_DIR.parent
SOURCE_ROOT = SUBMISSION_ROOT / "01_source_code"

if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))


def create_connection(host, port, timeout=10):
    """Create a TCP connection with a timeout."""
    conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    conn.settimeout(timeout)
    conn.connect((host, port))
    return conn


def send_msg(conn, msg_type, data):
    """Send a project frame: 4-byte length header + UTF-8 JSON body."""
    msg = {"type": msg_type, "data": data}
    msg_bytes = json.dumps(msg, ensure_ascii=False).encode("utf-8")
    length = len(msg_bytes).to_bytes(4, byteorder="big")
    conn.sendall(length + msg_bytes)


def recv_exact(conn, size):
    """Receive an exact number of bytes to handle TCP fragmentation."""
    chunks = []
    remaining = size
    while remaining > 0:
        chunk = conn.recv(remaining)
        if not chunk:
            return None
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def recv_msg(conn, timeout=5):
    """Receive one framed project message."""
    conn.settimeout(timeout)
    try:
        length_bytes = recv_exact(conn, 4)
        if not length_bytes:
            return None
        msg_len = int.from_bytes(length_bytes, byteorder="big")
        msg_data = recv_exact(conn, msg_len)
        if not msg_data:
            return None
        return json.loads(msg_data.decode("utf-8"))
    except Exception:
        return None
