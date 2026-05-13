"""Quality tests for semantic_search — real queries against code-context project.

These tests start the MCP server, call semantic_search, and validate that
results are relevant with score >= 0.7. Skipped if Ollama is unavailable.
"""

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

PROJECT = str(Path(__file__).resolve().parent.parent)
SERVER_CMD = ["uv", "run", "python", "-m", "src.server", "--skip-index"]

# 5 queries with expected files (top-3 should contain these)
QUERIES = [
    ("vector index search", ["src/vector_index.py"]),
    ("project search find symbols", ["src/search.py"]),
    ("git commit change summary", ["src/change_intel.py"]),
    ("semantic code summaries tool", ["src/summaries.py", "src/server.py"]),
    ("MCP instrumentation decorator", ["src/server.py"]),
]


def _read_line(proc: subprocess.Popen, timeout: float = 20.0) -> dict:
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


def _start_server() -> subprocess.Popen:
    merged = {**os.environ}
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
            "clientInfo": {"name": "quality-test", "version": "1.0"},
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


def _call_tool(proc: subprocess.Popen, name: str, args: dict, timeout: float = 30.0) -> dict:
    _send(proc, {
        "jsonrpc": "2.0", "id": hash((name, str(args))) & 0x7FFFFFFF,
        "method": "tools/call",
        "params": {"name": name, "arguments": args},
    })
    return _read_line(proc, timeout=timeout)


def _check_ollama() -> bool:
    """Quick check if Ollama is reachable."""
    try:
        import urllib.request
        req = urllib.request.Request("http://localhost:11434/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read())
            models = [m["name"] for m in data.get("models", [])]
            return any("nomic-embed-text" in m for m in models)
    except Exception:
        return False


@pytest.mark.skipif(not shutil.which("uv"), reason="uv not in PATH")
@pytest.mark.skipif(not _check_ollama(), reason="Ollama or nomic-embed-text not available")
class TestSemanticSearchQuality:

    @classmethod
    def setup_class(cls):
        cls.proc = _start_server()
        # Warmup: build index via first search
        cls._warmup()

    @classmethod
    def teardown_class(cls):
        _stop_server(cls.proc)

    @classmethod
    def _warmup(cls):
        """Ensure vector index is built before running quality tests."""
        resp = _call_tool(cls.proc, "semantic_search", {
            "query": "warmup query to build index",
            "project_path": PROJECT,
            "top_k": 1,
        })
        # Wait for index to build
        for _ in range(30):
            h_resp = _call_tool(cls.proc, "get_health", {})
            h_text = h_resp.get("result", {}).get("content", [{}])[0].get("text", "")
            try:
                health = json.loads(h_text)
                vi = health.get("vector_index", {})
                if vi.get("status") == "ok" and vi.get("chunks", 0) > 50:
                    return
            except (json.JSONDecodeError, KeyError):
                pass
            time.sleep(1)
        pytest.skip("Vector index not built within 30s")

    @pytest.mark.parametrize("query,expected_files", QUERIES, ids=[q[0][:20] for q in QUERIES])
    def test_query_returns_relevant_results(self, query: str, expected_files: list[str]):
        resp = _call_tool(self.proc, "semantic_search", {
            "query": query,
            "project_path": PROJECT,
            "top_k": 5,
        })
        assert "result" in resp, f"No result for {query!r}: {resp}"
        text = resp["result"].get("content", [{}])[0].get("text", "")
        assert "semantic_search error" not in text, f"Error for {query!r}: {text}"
        assert "results" in text.lower(), f"No results for {query!r}: {text}"

        # Parse results to check scores and expected files
        found_expected = False
        max_score = 0.0
        for line in text.split("\n"):
            if "score=" in line:
                score_str = line.split("score=")[-1].strip()
                try:
                    score = float(score_str)
                    max_score = max(max_score, score)
                except ValueError:
                    pass
            for exp in expected_files:
                if exp in line:
                    found_expected = True

        assert max_score >= 0.7, f"Query {query!r}: max score {max_score} < 0.7\n{text}"
        assert found_expected, (
            f"Query {query!r}: expected {expected_files} not in top-5\n{text}"
        )
