"""Embedding-based vector index for semantic code search.

Storage layout:
    ~/.code-context-cache/vectors/<project_hash>/
        chunks.json      — chunk metadata (file, line, symbol, snippet)
        vectors.npy      — float32 matrix  (N × D)

Indexing is lazy: on first search the project is indexed, subsequent calls
re-index only files whose mtime/hash changed since last run.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

from llm.router import LLMRouter


# ── data model ────────────────────────────────────────────────────────────────


@dataclass
class Chunk:
    chunk_id: str
    file: str
    line_start: int
    symbol: str
    snippet: str
    file_hash: str


@dataclass
class SearchResult:
    file: str
    line: int
    symbol: str
    snippet: str
    score: float


@dataclass
class IndexMetadata:
    provider_name: str
    model: str
    embedding_dim: int


# ── cosine similarity (pure stdlib + numpy) ───────────────────────────────────


def _cosine(a: list[float], b: "np.ndarray") -> float:  # type: ignore[name-defined]
    import numpy as np

    av = np.array(a, dtype=np.float32)
    norm_a = float(np.linalg.norm(av))
    norm_b = float(np.linalg.norm(b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(av, b) / (norm_a * norm_b))


# ── persistence helpers ───────────────────────────────────────────────────────


def _project_hash(project_path: Path) -> str:
    return hashlib.md5(str(project_path.resolve()).encode()).hexdigest()[:12]


def _file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def _cache_dir(project_path: Path) -> Path:
    base = Path.home() / ".code-context-cache" / "vectors" / _project_hash(project_path)
    base.mkdir(parents=True, exist_ok=True)
    return base


# ── index ─────────────────────────────────────────────────────────────────────

_SOURCE_EXTENSIONS = {".py", ".ts", ".tsx", ".js", ".jsx", ".swift", ".go", ".rs", ".dart", ".md", ".mdx", ".markdown"}
_MAX_SNIPPET_CHARS = 400


def _iter_source_files(project_path: Path):
    for path in project_path.rglob("*"):
        if path.suffix not in _SOURCE_EXTENSIONS:
            continue
        parts = set(path.parts)
        if parts & {"node_modules", ".venv", "venv", "target", "build", "dist", ".build", "Pods"}:
            continue
        if path.is_file():
            yield path


def _extract_chunks(file_path: Path, project_path: Path) -> list[Chunk]:
    """Read file and produce one Chunk per top-level symbol (or whole file if tiny)."""
    try:
        text = file_path.read_text(errors="replace")
    except OSError:
        return []

    fhash = _file_hash(file_path)
    rel = str(file_path.relative_to(project_path))
    lines = text.splitlines()

    # Try to chunk by top-level definitions (simple heuristic, no tree-sitter here
    # to keep this module dependency-free — tree-sitter is used in search.py already)
    chunks: list[Chunk] = []
    current_symbol = "<module>"
    current_start = 1
    buffer: list[str] = []

    def _flush(symbol: str, start: int, buf: list[str]) -> None:
        snippet = "\n".join(buf).strip()[:_MAX_SNIPPET_CHARS]
        if not snippet:
            return
        cid = hashlib.md5(f"{rel}:{start}:{symbol}".encode()).hexdigest()[:12]
        chunks.append(Chunk(chunk_id=cid, file=rel, line_start=start, symbol=symbol, snippet=snippet, file_hash=fhash))

    import re

    _def_re = re.compile(r"^(def |class |func |fn |function |pub fn |public |private |@interface |struct |enum )\s*(\w+)")
    _md_heading_re = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*$")

    if file_path.suffix.lower() in {".md", ".markdown", ".mdx"}:
        chunks = []
        heading = "<document>"
        start = 1
        buf: list[str] = []

        def _flush_md(title: str, line_start: int, lines_buf: list[str]) -> None:
            snippet = "\n".join(lines_buf).strip()[:_MAX_SNIPPET_CHARS]
            if not snippet:
                return
            cid = hashlib.md5(f"{rel}:{line_start}:{title}".encode()).hexdigest()[:12]
            chunks.append(
                Chunk(
                    chunk_id=cid,
                    file=rel,
                    line_start=line_start,
                    symbol=title,
                    snippet=snippet,
                    file_hash=fhash,
                )
            )

        for i, line in enumerate(lines, 1):
            m = _md_heading_re.match(line)
            if m:
                if buf:
                    _flush_md(heading, start, buf)
                heading = m.group(1).strip() or "<section>"
                start = i
                buf = [line]
            else:
                buf.append(line)

        _flush_md(heading, start, buf)
        if chunks:
            return chunks

    for i, line in enumerate(lines, 1):
        m = _def_re.match(line.lstrip())
        if m:
            if buffer:
                _flush(current_symbol, current_start, buffer)
            current_symbol = m.group(2)
            current_start = i
            buffer = [line]
        else:
            buffer.append(line)

    _flush(current_symbol, current_start, buffer)

    # If file is tiny and produced no chunks, emit one whole-file chunk
    if not chunks and text.strip():
        cid = hashlib.md5(f"{rel}:1:file".encode()).hexdigest()[:12]
        chunks.append(Chunk(chunk_id=cid, file=rel, line_start=1, symbol=rel, snippet=text[:_MAX_SNIPPET_CHARS], file_hash=fhash))

    return chunks


class VectorIndex:
    """Persistent embedding index for a single project.

    Usage:
        idx = VectorIndex(project_path, router, local_model="nomic-embed-text")
        results = idx.search("user authentication token", top_k=5)
    """

    def __init__(
        self,
        project_path: str | Path,
        router: LLMRouter,
        local_model: str = "nomic-embed-text",
        remote_model: str = "text-embedding-3-small",
    ) -> None:
        self._project = Path(project_path)
        self._router = router
        self._local_model = local_model
        self._remote_model = remote_model
        self._cache = _cache_dir(self._project)

        self._chunks: list[Chunk] = []
        self._vectors: Optional["np.ndarray"] = None  # type: ignore[name-defined]
        self._meta: Optional[IndexMetadata] = None
        self._loaded = False

    # ── public ────────────────────────────────────────────────────────────

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        """Return top-k chunks most similar to *query*."""
        import numpy as np

        self._ensure_indexed()
        if not self._chunks or self._vectors is None:
            return []

        query_response = self._router.embed(
            text=query,
            local_model=self._local_model,
            remote_model=self._remote_model,
        )
        if not query_response.ok or query_response.embedding is None:
            raise RuntimeError(query_response.error_reason or "provider unavailable")

        query_meta = IndexMetadata(
            provider_name=query_response.provider,
            model=query_response.model,
            embedding_dim=len(query_response.embedding),
        )
        if self._meta and self._meta != query_meta:
            self.index_project(force=True)
            query_response = self._router.embed(
                text=query,
                local_model=self._local_model,
                remote_model=self._remote_model,
            )
            if not query_response.ok or query_response.embedding is None:
                raise RuntimeError(query_response.error_reason or "provider unavailable")
            query_meta = IndexMetadata(
                provider_name=query_response.provider,
                model=query_response.model,
                embedding_dim=len(query_response.embedding),
            )

        self._meta = query_meta
        query_vec = query_response.embedding
        qv = np.array(query_vec, dtype=np.float32)
        norm = float(np.linalg.norm(qv))
        if norm == 0:
            return []
        qv /= norm

        # Vectorised cosine: matrix (N×D) · query (D,) → (N,)
        norms = np.linalg.norm(self._vectors, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)
        normed = self._vectors / norms
        scores: "np.ndarray" = normed @ qv

        k = min(top_k, len(self._chunks))
        top_indices = scores.argsort()[-k:][::-1]
        max_score = float(max(float(scores[i]) for i in top_indices)) if k > 0 else 0.0

        seen_files: set[str] = set()
        output: list[SearchResult] = []
        for i in top_indices:
            raw_score = float(scores[i])
            if raw_score <= 0:
                continue
            file_name = self._chunks[i].file
            if file_name in seen_files:
                continue
            seen_files.add(file_name)
            normalized = raw_score / max_score if max_score > 0 else raw_score
            output.append(
                SearchResult(
                    file=file_name,
                    line=self._chunks[i].line_start,
                    symbol=self._chunks[i].symbol,
                    snippet=self._chunks[i].snippet,
                    score=round(float(normalized), 4),
                )
            )

        return output

    def index_project(self, force: bool = False) -> int:
        """Index (or incrementally update) the project. Returns number of chunks embedded."""
        import numpy as np

        self._load_from_disk()

        existing: dict[str, Chunk] = {c.chunk_id: c for c in self._chunks}
        existing_vecs: dict[str, list[float]] = {}
        if self._vectors is not None and len(self._vectors) == len(self._chunks):
            for i, c in enumerate(self._chunks):
                existing_vecs[c.chunk_id] = self._vectors[i].tolist()

        # Discover current chunks
        all_chunks: list[Chunk] = []
        for fpath in _iter_source_files(self._project):
            all_chunks.extend(_extract_chunks(fpath, self._project))

        # Determine which need (re)embedding
        new_chunks: list[Chunk] = []
        reuse_chunks: list[Chunk] = []
        for ch in all_chunks:
            old = existing.get(ch.chunk_id)
            if not force and old and old.file_hash == ch.file_hash and ch.chunk_id in existing_vecs:
                reuse_chunks.append(ch)
            else:
                new_chunks.append(ch)

        if not new_chunks and reuse_chunks:
            self._chunks = reuse_chunks
            return 0  # nothing changed

        # Embed new chunks
        new_vecs: list[list[float]] = []
        expected_meta: Optional[IndexMetadata] = None
        for ch in new_chunks:
            response = self._router.embed(
                text=f"{ch.symbol}\n{ch.snippet}",
                local_model=self._local_model,
                remote_model=self._remote_model,
            )
            if not response.ok or response.embedding is None:
                raise RuntimeError(response.error_reason or "provider unavailable")

            meta = IndexMetadata(
                provider_name=response.provider,
                model=response.model,
                embedding_dim=len(response.embedding),
            )
            if expected_meta is None:
                expected_meta = meta
            elif expected_meta != meta:
                raise RuntimeError("provider unavailable: embedding provider/model changed during indexing")
            new_vecs.append(response.embedding)

        # Merge
        ordered_chunks = reuse_chunks + new_chunks
        reuse_vecs = [existing_vecs[c.chunk_id] for c in reuse_chunks if c.chunk_id in existing_vecs]
        all_vecs = reuse_vecs + new_vecs

        self._chunks = ordered_chunks
        self._vectors = np.array(all_vecs, dtype=np.float32) if all_vecs else None
        if expected_meta:
            self._meta = expected_meta
        self._save_to_disk()
        return len(new_chunks)

    # ── persistence ───────────────────────────────────────────────────────

    def _ensure_indexed(self) -> None:
        if not self._loaded:
            self._load_from_disk()
            self._loaded = True
        if not self._chunks:
            self.index_project()

    def _load_from_disk(self) -> None:
        import numpy as np

        chunks_path = self._cache / "chunks.json"
        vectors_path = self._cache / "vectors.npy"
        meta_path = self._cache / "meta.json"
        if not chunks_path.exists() or not vectors_path.exists():
            return
        try:
            raw = json.loads(chunks_path.read_text())
            self._chunks = [Chunk(**c) for c in raw]
            self._vectors = np.load(str(vectors_path))
            if meta_path.exists():
                self._meta = IndexMetadata(**json.loads(meta_path.read_text()))
            else:
                # Legacy index without provider/model metadata must be rebuilt.
                self._chunks = []
                self._vectors = None
            self._loaded = True
        except Exception:
            self._chunks = []
            self._vectors = None
            self._meta = None

    def _save_to_disk(self) -> None:
        import numpy as np

        chunks_path = self._cache / "chunks.json"
        vectors_path = self._cache / "vectors.npy"
        meta_path = self._cache / "meta.json"
        chunks_path.write_text(json.dumps([asdict(c) for c in self._chunks], indent=2))
        if self._vectors is not None:
            np.save(str(vectors_path), self._vectors)
        if self._meta is not None:
            meta_path.write_text(json.dumps(asdict(self._meta), indent=2))
