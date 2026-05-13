"""Integration tests for end-to-end flow: summarize → draft → approve → commit."""

import os
import subprocess
import tempfile
from pathlib import Path

from change_intel import CompactChangeIntel, CommitGate, generate_commit_draft


def _git(*args: str, cwd: Path):
    subprocess.run(("git",) + args, cwd=cwd, capture_output=True, text=True, check=False)


def _make_repo() -> Path:
    tmp = Path(tempfile.mkdtemp())
    _git("init", cwd=tmp)
    _git("config", "user.email", "test@test.com", cwd=tmp)
    _git("config", "user.name", "Test", cwd=tmp)
    return tmp


# ── end-to-end integration (4.4) ────────────────────────────────────────


def test_end_to_end_commit_flow():
    repo = _make_repo()

    # Create initial file and commit
    (repo / "src").mkdir(exist_ok=True)
    (repo / "src/main.py").write_text("print('hello')\n")
    _git("add", ".", cwd=repo)
    _git("commit", "-m", "init", cwd=repo)

    # Make a change
    (repo / "src/main.py").write_text("print('hello world')\ndef greet(name): pass\n")
    (repo / "src/utils.py").write_text("def helper(): return 42\n")

    # 1. Summarize
    intel = CompactChangeIntel(repo)
    cc = intel.summarize_working_changes(staged=False, unstaged=True, respect_hygiene=True)
    assert cc.change_count == 2

    # 2. Draft
    draft = generate_commit_draft(cc)
    assert draft.message
    assert draft.rationale
    assert not draft.fallback
    assert draft.confidence > 0

    # 3. Approve gate
    gate = CommitGate()
    assert not gate.can_commit
    gate.approve(message="feat: add greet function and utils module")
    assert gate.can_commit
    assert gate.state == CommitGate.EDITED

    # 4. Execute commit
    _git("add", ".", cwd=repo)
    result = subprocess.run(
        ["git", "commit", "-m", gate._approved_message or ""],
        capture_output=True, text=True, cwd=repo, timeout=30,
    )
    assert result.returncode == 0, f"Commit failed: {result.stderr}"

    # Verify
    log = subprocess.run(["git", "log", "--oneline", "-1"], capture_output=True, text=True, cwd=repo)
    assert "greet" in log.stdout or "utils" in log.stdout


def test_no_changes_draft():
    repo = _make_repo()
    (repo / "readme.md").write_text("# project\n")
    _git("add", ".", cwd=repo)
    _git("commit", "-m", "init", cwd=repo)

    intel = CompactChangeIntel(repo)
    cc = intel.summarize_working_changes()
    assert cc.change_count == 0

    draft = generate_commit_draft(cc)
    assert draft.fallback


def test_semantic_search_returns_unavailable_when_providers_down():
    import os
    import tempfile
    from pathlib import Path
    import server

    orig_url = os.environ.get("CC_OLLAMA_URL")
    orig_key = os.environ.get("CC_OPENROUTER_API_KEY")
    try:
        os.environ["CC_OLLAMA_URL"] = "http://127.0.0.1:1"
        if "CC_OPENROUTER_API_KEY" in os.environ:
            del os.environ["CC_OPENROUTER_API_KEY"]
        server._llm_router = None
        server._vector_indexes = {}

        project = Path(tempfile.mkdtemp())
        (project / "test.py").write_text("x = 1\ny = 2\n")

        result = server.semantic_search(query="test", project_path=str(project))
        assert "unavailable" in result.lower() or "error" in result.lower(), f"Expected unavailable/error, got: {result}"
        assert "решение" in result.lower() or "ollama" in result.lower(), f"Expected actionable message, got: {result}"
    finally:
        if orig_url is not None:
            os.environ["CC_OLLAMA_URL"] = orig_url
        else:
            os.environ.pop("CC_OLLAMA_URL", None)
        if orig_key is not None:
            os.environ["CC_OPENROUTER_API_KEY"] = orig_key
        else:
            os.environ.pop("CC_OPENROUTER_API_KEY", None)
        server._llm_router = None
        server._vector_indexes = {}


def test_semantic_search_empty_query_returns_message():
    import server
    result = server.semantic_search(query="", project_path="/tmp")
    assert "empty query" in result.lower(), f"Expected empty query message, got: {result}"
    result = server.semantic_search(query="   ", project_path="/tmp")
    assert "empty query" in result.lower(), f"Expected empty query message for whitespace, got: {result}"

