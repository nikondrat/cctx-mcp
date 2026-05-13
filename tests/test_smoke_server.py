"""Smoke test: launch MCP server via subprocess, exercise JSON-RPC tools."""

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

SERVER_CMD = ["uv", "run", "python", "-m", "code_context.server"]
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
            "clientInfo": {"name": "smoke-test", "version": "1.0"},
        },
    })
    resp = _read_line(proc)
    assert "result" in resp and resp.get("id") == 1, f"Init failed: {resp}"
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


def test_find_symbols_returns_list():
    if shutil.which("uv") is None:
        pytest.skip("uv not in PATH")
    proc = _start_server()
    try:
        resp = _call_tool(proc, "find_symbols", {"project_path": PROJECT, "name": "VectorIndex"})
        assert "result" in resp, f"No result: {resp}"
        text = resp["result"].get("content", [{}])[0].get("text", "")
        assert "VectorIndex" in text, f"Expected VectorIndex in: {text}"
    finally:
        _stop_server(proc)


def test_semantic_search_unavailable():
    if shutil.which("uv") is None:
        pytest.skip("uv not in PATH")
    env = {
        "CC_OLLAMA_URL": "http://127.0.0.1:1",
        "CC_OPENROUTER_API_KEY": "",
    }
    proc = _start_server(env=env)
    try:
        resp = _call_tool(proc, "semantic_search", {
            "query": "test query", "project_path": PROJECT,
        })
        assert "result" in resp, f"No result: {resp}"
        text = resp["result"].get("content", [{}])[0].get("text", "")
        assert "unavailable" in text.lower() or "error" in text.lower(), f"Expected unavailable/error, got: {text}"
    finally:
        _stop_server(proc)


def test_core_tools_respond():
    if shutil.which("uv") is None:
        pytest.skip("uv not in PATH")
    proc = _start_server()
    try:
        tools = {
            "find_symbols": {"project_path": PROJECT, "name": "VectorIndex"},
            "code_search": {"project_path": PROJECT, "pattern": "def ", "file_pattern": "*.py"},
            "smart_read": {"file_path": str(Path(PROJECT) / "src/server.py")},
            "get_config": {},
            "get_metrics_report": {},
            "semantic_search": {"query": "test", "project_path": PROJECT, "top_k": 1},
        }
        for name, args in tools.items():
            resp = _call_tool(proc, name, args)
            text = resp.get("result", {}).get("content", [{}])[0].get("text", "")
            assert "error" not in resp, f"{name} returned error: {resp}"
            assert text, f"{name} returned empty text"
    finally:
        _stop_server(proc)
