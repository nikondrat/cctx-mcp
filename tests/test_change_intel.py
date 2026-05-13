"""Tests for compact change intelligence — representative change sets."""

import json

from code_context.change_intel import (
    ChangedFile,
    CompactChange,
    CompactChangeIntel,
    CommitGate,
    _draft_subject,
    _draft_rationale,
    _compute_confidence,
    _is_noise_path,
    generate_commit_draft,
)


def make_cc(files: list[ChangedFile]) -> CompactChange:
    cc = CompactChange()
    cc.files = files
    cc.change_count = len(files)
    cc.total_additions = sum(f.additions for f in files)
    cc.total_deletions = sum(f.deletions for f in files)
    cc.change_types = CompactChangeIntel._classify_change_types(files)
    cc.intent_cues = CompactChangeIntel._extract_intent_cues(files)
    cc.summary = CompactChangeIntel._build_summary(cc)
    return cc


# ── JSON contract (3.3) ─────────────────────────────────────────────────


def test_json_contract():
    files = [ChangedFile(path="src/server.py", change_type="modified", additions=5, deletions=2)]
    cc = make_cc(files)
    raw = cc.to_json()
    data = json.loads(raw)
    assert "files" in data
    assert "change_count" in data
    assert "total_additions" in data
    assert "total_deletions" in data
    assert "summary" in data
    assert "change_types" in data
    assert "intent_cues" in data
    assert data["change_count"] == 1
    assert data["total_additions"] == 5
    assert data["total_deletions"] == 2


# ── single-file fix (3.4) ───────────────────────────────────────────────


def test_single_file_fix():
    files = [ChangedFile(path="src/bugfix.py", change_type="modified", additions=3, deletions=1)]
    cc = make_cc(files)
    draft = generate_commit_draft(cc)
    assert "fix" in draft.message or "fix" in draft.subject if hasattr(draft, "subject") else True
    assert draft.confidence > 0.5
    assert not draft.fallback


# ── multi-module feature (3.4) ───────────────────────────────────────────


def test_multi_module_feature():
    files = [
        ChangedFile(path="src/new_feature.py", change_type="added", additions=45, deletions=0),
        ChangedFile(path="src/new_feature_test.py", change_type="added", additions=20, deletions=0),
        ChangedFile(path="src/__init__.py", change_type="modified", additions=1, deletions=0),
    ]
    cc = make_cc(files)
    draft = generate_commit_draft(cc)

    assert len(cc.files) == 3
    assert "added" in cc.change_types
    assert any("module" in c for c in cc.intent_cues)
    assert "feat" in draft.message or "add" in draft.message
    assert not draft.fallback


# ── refactor-heavy update (3.4) ──────────────────────────────────────────


def test_refactor_heavy_update():
    files = [
        ChangedFile(path="src/legacy.py", change_type="modified", additions=10, deletions=40),
        ChangedFile(path="src/new_impl.py", change_type="added", additions=80, deletions=0),
        ChangedFile(path="src/utils.py", change_type="modified", additions=5, deletions=5),
    ]
    cc = make_cc(files)
    draft = generate_commit_draft(cc)

    assert cc.total_additions == 95
    assert cc.total_deletions == 45
    assert not draft.fallback


# ── hygiene filters (3.2) ────────────────────────────────────────────────


def test_hygiene_noise_filter():
    assert _is_noise_path("node_modules/foo/bar.js")
    assert _is_noise_path("package-lock.json")
    assert _is_noise_path("target/debug/lib.rlib")
    assert _is_noise_path("Pods/SomePod/SomeFile.swift")
    assert _is_noise_path(".venv/lib/python3.10/site-packages/pkg.py")
    assert not _is_noise_path("src/server.py")
    assert not _is_noise_path("tests/test_auth.py")
    assert not _is_noise_path("README.md")


# ── empty changes (4.2 fallback) ────────────────────────────────────────


def test_no_changes_fallback():
    cc = make_cc([])
    draft = generate_commit_draft(cc)
    assert draft.fallback
    assert draft.confidence == 1.0


# ── commit gate (4.3) ───────────────────────────────────────────────────


def test_commit_gate():
    gate = CommitGate()
    assert gate.state == CommitGate.PENDING
    assert not gate.can_commit

    gate.approve()
    assert gate.can_commit
    assert gate.state == CommitGate.APPROVED

    gate.reject()
    assert not gate.can_commit
    assert gate.state == CommitGate.REJECTED


def test_commit_gate_edited_message():
    gate = CommitGate()
    gate.approve(message="fix: resolve login bug")
    assert gate.can_commit
    assert gate.state == CommitGate.EDITED


# ── confidence scoring (4.2) ────────────────────────────────────────────


def test_confidence_small_change():
    files = [
        ChangedFile(path="src/foo.py", change_type="modified", additions=2, deletions=1),
        ChangedFile(path="tests/test_foo.py", change_type="added", additions=10, deletions=0),
    ]
    cc = make_cc(files)
    assert cc.intent_cues  # test file → intent cue
    assert _compute_confidence(cc) > 0.5
