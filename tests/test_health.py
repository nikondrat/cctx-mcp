"""Tests for get_health() MCP tool."""

import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import pytest

SERVER_CMD = ["uv", "run", "python", "-m", "code_context.server", "--skip-index"]
PROJECT = str(Path(__file__).resolve().parent.parent)


def _read_line(proc: subprocess.Popen, timeout: float = 15.0) -> dict:
    started = time.monotonic()
    buf = b""
    while time.monotonic() - started < timeout:
        if proc.stdout is None:
            raise RuntimeError("proc.stdout is None")
        line = proc.stdout.readline()
        if line:
            buf += line
            try:
                return json.loads(buf)
            except json.JSONDecodeError:
                continue
        if proc.poll() is not None:
            break
        time.sleep(0.05)
    raise TimeoutError(f"No JSON-RPC response within {timeout}s, buf={buf!r}")


def _send(proc: subprocess.Popen, msg: dict):
    if proc.stdin is None:
        raise RuntimeError("proc.stdin is None")
    data = json.dumps(msg).encode() + b"\n"
    proc.stdin.write(data)
    proc.stdin.flush()


def _start_server(env: dict | None = None) -> subprocess.Popen:
    merged = {**os.environ, **(env or {})}
    merged.pop("CC_OPENROUTER_API_KEY", None)
    proc = subprocess.Popen(
        SERVER_CMD,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False,
        cwd=PROJECT,
        env=merged,
    )
    _send(proc, {
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "health-test", "version": "1.0"},
        },
    })
    resp = _read_line(proc)
    assert resp.get("id") == 1, f"Init failed: {resp}"
    _send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})
    return proc


def _stop_server(proc: subprocess.Popen):
    try:
        _send(proc, {"jsonrpc": "2.0", "id": 999, "method": "shutdown"})
        proc.wait(timeout=5)
    except Exception:
        proc.kill()


def _call_tool(proc: subprocess.Popen, name: str, args: dict, timeout: float = 15.0) -> dict:
    _send(proc, {
        "jsonrpc": "2.0", "id": hash((name, str(args))) & 0x7FFFFFFF,
        "method": "tools/call",
        "params": {"name": name, "arguments": args},
    })
    return _read_line(proc, timeout=timeout)


def test_uv_available():
    if shutil.which("uv") is None:
        pytest.skip("uv not in PATH")


def test_get_health_returns_json():
    if shutil.which("uv") is None:
        pytest.skip("uv not in PATH")
    proc = _start_server()
    try:
        resp = _call_tool(proc, "get_health", {})
        assert "result" in resp, f"No result: {resp}"
        text = resp["result"].get("content", [{}])[0].get("text", "")
        data = json.loads(text)
        assert "server" in data, f"Missing server field: {data}"
        assert "ollama" in data, f"Missing ollama field: {data}"
        assert "vector_index" in data, f"Missing vector_index field: {data}"
        assert "tree_sitter" in data, f"Missing tree_sitter field: {data}"
        assert data["server"]["version"], f"Empty version: {data}"
    finally:
        _stop_server(proc)


def test_get_health_ollama_status():
    if shutil.which("uv") is None:
        pytest.skip("uv not in PATH")
    proc = _start_server()
    try:
        resp = _call_tool(proc, "get_health", {})
        text = resp["result"].get("content", [{}])[0].get("text", "")
        data = json.loads(text)
        assert data["ollama"]["status"] in ("ok", "error"), f"Unexpected ollama status: {data}"
        if data["ollama"]["status"] == "ok":
            assert "latency_ms" in data["ollama"]
    finally:
        _stop_server(proc)


def test_get_health_embedding_model():
    if shutil.which("uv") is None:
        pytest.skip("uv not in PATH")
    proc = _start_server()
    try:
        resp = _call_tool(proc, "get_health", {})
        text = resp["result"].get("content", [{}])[0].get("text", "")
        data = json.loads(text)
        assert "embedding_model" in data, f"Missing embedding_model: {data}"
        assert data["embedding_model"]["status"] in ("ok", "error", "unknown")
    finally:
        _stop_server(proc)
