"""Compact change-intelligence: git-delta summarizer, hygiene filters, commit drafting."""

import json
import os
import re
import subprocess
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ── noise / hygiene filters ─────────────────────────────────────────────

HYGIENE_EXCLUDE_PATTERNS = (
    # build artifacts
    r"\.(pyc|pyo|class|o|so|dylib|dll|exe|wasm)$",
    r"^target/",
    r"^build/",
    r"^dist/",
    r"^\.build/",
    # lock / generated
    r"(package-lock\.json|yarn\.lock|pnpm-lock\.yaml|Cargo\.lock|Gemfile\.lock|poetry\.lock)$",
    r"(gradle\.lockfile|\.gradle/|\.idea/|\.iml$)",
    r"(generated|\.pb\.|_pb2\.py|_grpc_pb2\.py)$",
    # vendored / third-party
    r"^(vendor/|third_party/|node_modules/|Pods/|\.venv/|venv/)",
    # large binary-ish
    r"\.(png|jpg|jpeg|gif|ico|svg|woff|woff2|eot|ttf|otf|pdf|mp4|mp3|zip|tar|gz|bz2)$",
    # env / secrets
    r"(\.env|\.credentials|\.secret)",
    # changelogs — too noisy
    r"(CHANGELOG|changelog|CHANGES)",
)


def _is_noise_path(rel_path: str) -> bool:
    for p in HYGIENE_EXCLUDE_PATTERNS:
        if re.search(p, rel_path):
            return True
    return False


# ── data contracts ──────────────────────────────────────────────────────


@dataclass
class ChangedFile:
    path: str
    change_type: str  # added | modified | deleted | renamed
    additions: int = 0
    deletions: int = 0


@dataclass
class CompactChange:
    files: list[ChangedFile] = field(default_factory=list)
    change_count: int = 0
    total_additions: int = 0
    total_deletions: int = 0
    summary: str = ""
    change_types: list[str] = field(default_factory=list)
    intent_cues: list[str] = field(default_factory=list)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(asdict(self), indent=indent)


@dataclass
class CommitDraft:
    message: str
    rationale: str
    confidence: float = 0.0
    fallback: bool = False
    source: str = "heuristic"  # "heuristic" | "ollama:<model>"


# ── git-delta summarizer ────────────────────────────────────────────────


class CompactChangeIntel:
    """Produce compact, structured change summaries from git diffs."""

    def __init__(self, repo_path: Optional[Path] = None):
        self._repo = repo_path or Path.cwd()

    # ── public API ───────────────────────────────────────────────────────

    def summarize_working_changes(
        self, staged: bool = False, unstaged: bool = True, respect_hygiene: bool = True
    ) -> CompactChange:
        files = self._get_changed_files(staged=staged, unstaged=unstaged)
        if respect_hygiene:
            files = [f for f in files if not _is_noise_path(f.path)]

        cc = CompactChange()
        cc.files = files
        cc.change_count = len(files)
        cc.total_additions = sum(f.additions for f in files)
        cc.total_deletions = sum(f.deletions for f in files)
        cc.change_types = self._classify_change_types(files)
        cc.intent_cues = self._extract_intent_cues(files)
        cc.summary = self._build_summary(cc)
        return cc

    def draft_commit(self, cc: CompactChange) -> CommitDraft:
        """Generate a local commit draft from compact change intelligence."""
        return generate_commit_draft(cc)

    # ── git helpers ─────────────────────────────────────────────────────

    def _get_changed_files(
        self, staged: bool = False, unstaged: bool = True
    ) -> list[ChangedFile]:
        files: list[ChangedFile] = []

        if unstaged:
            raw = self._run_git("diff", "--numstat")
            for line in raw.strip().splitlines():
                f = self._parse_numstat(line)
                if f:
                    files.append(f)
            raw = self._run_git("ls-files", "--others", "--exclude-standard")
            for path in raw.strip().splitlines():
                if path.strip():
                    files.append(ChangedFile(path=path.strip(), change_type="added"))

        if staged:
            raw = self._run_git("diff", "--cached", "--numstat")
            for line in raw.strip().splitlines():
                f = self._parse_numstat(line)
                if f:
                    files.append(f)

        return files

    def _parse_numstat(self, line: str) -> Optional[ChangedFile]:
        parts = line.strip().split("\t")
        if len(parts) < 3:
            return None
        adds_str, dels_str, path = parts[0], parts[1], parts[2]
        if path == "-":
            return None
        adds = int(adds_str) if adds_str != "-" else 0
        dels = int(dels_str) if dels_str != "-" else 0
        ct = "modified"
        if adds_str == "-" and dels_str == "-":
            ct = "binary"
        return ChangedFile(path=path, change_type=ct, additions=adds, deletions=dels)

    def _run_git(self, *args: str) -> str:
        try:
            result = subprocess.run(
                ("git",) + args,
                capture_output=True,
                text=True,
                cwd=self._repo,
                timeout=30,
            )
            return result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return ""

    # ── classification / cues ────────────────────────────────────────────

    @staticmethod
    def _classify_change_types(files: list[ChangedFile]) -> list[str]:
        types = set()
        for f in files:
            types.add(f.change_type)
        return sorted(types)

    @staticmethod
    def _extract_intent_cues(files: list[ChangedFile]) -> list[str]:
        cues = []
        paths = [f.path for f in files if f.change_type != "deleted"]

        # module-level additions
        new_paths = [f.path for f in files if f.change_type == "added"]
        if new_paths:
            new_dirs = set(p.rsplit("/", 1)[0] if "/" in p else "." for p in new_paths)
            for d in new_dirs:
                cues.append(f"new module in {d}")

        # test changes
        test_files = [p for p in paths if "test" in p.lower() or "spec" in p.lower()]
        if test_files:
            cues.append("includes test changes")

        # config changes
        config_files = [
            p for p in paths
            if any(p.endswith(ext) for ext in (".json", ".yaml", ".yml", ".toml", ".ini"))
        ]
        if config_files:
            cues.append("configuration changes")

        # dependency changes
        dep_files = [p for p in paths if p.endswith((".pyproject", "Cargo.toml", "package.json"))]
        if dep_files:
            cues.append("dependency changes")

        return cues

    @staticmethod
    def _build_summary(cc: CompactChange) -> str:
        parts = [f"{cc.change_count} file(s) changed"]
        if cc.total_additions:
            parts.append(f"+{cc.total_additions}")
        if cc.total_deletions:
            parts.append(f"-{cc.total_deletions}")
        change_desc = ", ".join(cc.change_types) if cc.change_types else "modifications"
        parts.append(f"({change_desc})")
        return " ".join(parts)


# ── local commit drafting ───────────────────────────────────────────────


def generate_commit_draft(cc: CompactChange) -> CommitDraft:
    """Produce candidate commit message + rationale from compact change data."""
    if not cc.files:
        return CommitDraft(
            message="(no changes)",
            rationale="No changes detected.",
            confidence=1.0,
            fallback=True,
        )

    subject = _draft_subject(cc)
    body_lines = body_lines = []
    body_lines.append(f"# {cc.summary}")

    for f in cc.files[:20]:
        marker = {"added": "+", "deleted": "-", "modified": "~", "binary": "b"}.get(f.change_type, " ")
        body_lines.append(f"# {marker} {f.path}")
        if f.additions or f.deletions:
            body_lines[-1] += f" ({f.additions}+, {f.deletions}-)"
    if len(cc.files) > 20:
        body_lines.append(f"# ... +{len(cc.files) - 20} more")

    message = subject + "\n\n" + "\n".join(body_lines)
    rationale = _draft_rationale(cc)
    confidence = _compute_confidence(cc)

    return CommitDraft(
        message=message,
        rationale=rationale,
        confidence=confidence,
        fallback=False,
    )


def _draft_subject(cc: CompactChange) -> str:
    file_names = [Path(f.path).stem for f in cc.files[:3]]
    scope = ", ".join(file_names)
    if len(cc.files) > 3:
        scope += f" +{len(cc.files) - 3} more"

    if any("fix" in p.lower() or "bug" in p.lower() for f in cc.files for p in [f.path]):
        return f"fix: update {scope}"
    if any(f.change_type == "added" for f in cc.files):
        return f"feat: add {scope}"
    if any(f.path.endswith((".json", ".yaml", ".yml", ".toml", ".ini")) for f in cc.files):
        return f"chore: update configuration — {scope}"

    return f"refactor: update {scope}"


def _draft_rationale(cc: CompactChange) -> str:
    cues = cc.intent_cues
    if cues:
        return f"Detected: {'; '.join(cues)}."
    return f"{cc.change_count} files with {cc.total_additions} additions, {cc.total_deletions} deletions."


def _compute_confidence(cc: CompactChange) -> float:
    score = 0.5
    if cc.intent_cues:
        score += 0.2
    if cc.change_types:
        score += 0.1
    if 1 <= cc.change_count <= 5:
        score += 0.15
    elif cc.change_count <= 15:
        score += 0.05
    else:
        score -= 0.1
    return round(min(max(score, 0.0), 1.0), 2)


# ── approval gate ───────────────────────────────────────────────────────


class CommitGate:
    """Gate that blocks commit creation until cloud/user approves or edits."""

    PENDING = "pending"
    APPROVED = "approved"
    EDITED = "edited"
    REJECTED = "rejected"

    def __init__(self):
        self._state: str = self.PENDING
        self._approved_message: Optional[str] = None

    @property
    def state(self) -> str:
        return self._state

    @property
    def can_commit(self) -> bool:
        return self._state in (self.APPROVED, self.EDITED)

    def approve(self, message: Optional[str] = None):
        self._state = self.EDITED if message else self.APPROVED
        if message:
            self._approved_message = message

    def reject(self):
        self._state = self.REJECTED
