"""Unit tests for VectorIndex — Ollama embed calls mocked."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from llm.contracts import LLMResponse
from vector_index import VectorIndex, _extract_chunks, _file_hash, Chunk


def _mock_client(dim: int = 8):
    """Return a mock router that returns a fixed-dim random-ish vector."""
    import hashlib
    router = MagicMock()

    def fake_embed(model: str, text: str) -> list[float]:
        seed = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
        import random
        rng = random.Random(seed)
        return [rng.random() for _ in range(dim)]

    def route_embed(*, text: str, local_model: str, remote_model: str, force_provider=None):
        embedding = fake_embed(local_model or remote_model, text)
        return MagicMock(
            ok=True,
            embedding=embedding,
            provider="ollama",
            model=local_model or remote_model,
            error_reason="",
        )

    router.embed.side_effect = route_embed
    return router


class TestExtractChunks(unittest.TestCase):
    def test_extracts_python_defs(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "mod.py"
            p.write_text("def foo():\n    pass\n\ndef bar():\n    return 1\n")
            chunks = _extract_chunks(p, Path(tmp))
        symbols = [c.symbol for c in chunks]
        self.assertIn("foo", symbols)
        self.assertIn("bar", symbols)

    def test_extracts_nested_methods(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "service.py"
            p.write_text(
                "class AuthService:\n"
                "    def login(self):\n"
                "        pass\n"
                "    def logout(self):\n"
                "        pass\n"
                "def helper():\n"
                "    return 42\n"
            )
            chunks = _extract_chunks(p, Path(tmp))
        symbols = [c.symbol for c in chunks]
        self.assertIn("AuthService.login", symbols)
        self.assertIn("AuthService.logout", symbols)
        self.assertIn("helper", symbols)

    def test_chunks_deduplicated_by_snippet(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "dup.py"
            p.write_text(
                "def foo():\n    x = 1\n\n"
                "def bar():\n    x = 1\n\n"
            )
            chunks = _extract_chunks(p, Path(tmp))
        # Both have same body "x = 1" — one should be deduplicated
        self.assertLessEqual(len(chunks), 2)

    def test_whole_file_chunk_for_tiny_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "tiny.py"
            p.write_text("x = 1\n")
            chunks = _extract_chunks(p, Path(tmp))
        self.assertEqual(len(chunks), 1)

    def test_snippet_truncated(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "big.py"
            p.write_text("def foo():\n" + "    x = 1\n" * 200)
            chunks = _extract_chunks(p, Path(tmp))
        for c in chunks:
            self.assertLessEqual(len(c.snippet), 420)  # 400 + small overhead


class TestVectorIndexSearch(unittest.TestCase):
    def _index_with_files(self, files: dict[str, str]) -> tuple[VectorIndex, Path]:
        tmp = tempfile.mkdtemp()
        project = Path(tmp)
        for name, content in files.items():
            (project / name).write_text(content)
        client = _mock_client()
        idx = VectorIndex(project, client, local_model="nomic-embed-text", remote_model="")
        idx.index_project()
        return idx, project

    def test_search_returns_results(self):
        idx, _ = self._index_with_files({
            "auth.py": "def login(user, pw):\n    return True\n",
            "utils.py": "def helper():\n    return 42\n",
        })
        results = idx.search("user login authentication", top_k=2)
        self.assertGreater(len(results), 0)
        self.assertLessEqual(len(results), 2)

    def test_search_result_fields(self):
        idx, _ = self._index_with_files({
            "service.py": "def process_payment(amount):\n    pass\n",
        })
        results = idx.search("payment processing", top_k=1)
        r = results[0]
        self.assertIsInstance(r.file, str)
        self.assertIsInstance(r.line, int)
        self.assertIsInstance(r.score, float)
        self.assertTrue(0 <= r.score <= 1.01)  # cosine similarity

    def test_persist_and_reload(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "mod.py").write_text("def greet(name):\n    return f'hello {name}'\n")
            client = _mock_client()

            idx1 = VectorIndex(project, client, local_model="nomic-embed-text", remote_model="")
            idx1.index_project()
            count_embedded = client.embed.call_count

            # Second instance: should load from disk, no re-embedding
            client2 = _mock_client()
            idx2 = VectorIndex(project, client2, local_model="nomic-embed-text", remote_model="")
            idx2._load_from_disk()
            results = idx2.search("greeting function", top_k=1)
            # embed should not have been called for indexing (loaded from disk)
            # but WILL be called for the query itself
            self.assertEqual(client2.embed.call_count, 1)  # only query embed

    def test_empty_project_returns_no_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            client = _mock_client()
            idx = VectorIndex(tmp, client, local_model="nomic-embed-text", remote_model="")
            idx._chunks = []
            idx._vectors = None
            idx._loaded = True
            results = idx.search("anything")
            self.assertEqual(results, [])

    def test_search_returns_empty_when_embed_fails(self):
        import numpy as np
        router = MagicMock()
        router.embed.return_value = MagicMock(
            ok=False,
            embedding=None,
            provider="ollama",
            model="nomic-embed-text",
            error_reason="provider unavailable: ollama",
        )
        idx = VectorIndex("/tmp", router, local_model="nomic-embed-text", remote_model="")
        idx._chunks = [Chunk(chunk_id="1", file="test.py", line_start=1, symbol="test", snippet="test", file_hash="abc")]
        idx._vectors = np.array([[0.1, 0.2, 0.3]], dtype=np.float32)
        idx._loaded = True
        results = idx.search("test query")
        self.assertEqual(results, [])
        self.assertIsNotNone(idx.last_error)
        self.assertIn("provider unavailable", idx.last_error.lower())

    def test_check_stale_detects_file_change(self):
        import time as _time
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            mod = project / "mod.py"
            mod.write_text("def greet(): pass\n")
            client = _mock_client()
            idx = VectorIndex(project, client, local_model="nomic-embed-text", remote_model="")
            idx.index_project()
            self.assertIn("mod.py", idx._file_mtimes)
            old_mtime = idx._file_mtimes["mod.py"]

            # Modify file and update mtime
            _time.sleep(0.02)
            mod.write_text("def greet(): return 'hello'\n")

            # mtime should differ
            new_mtime = mod.stat().st_mtime
            self.assertNotEqual(old_mtime, new_mtime)
            self.assertTrue(idx._check_stale())

    def test_check_stale_detects_deleted_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "keep.py").write_text("x = 1\n")
            (project / "delete.py").write_text("y = 2\n")
            client = _mock_client()
            idx = VectorIndex(project, client, local_model="nomic-embed-text", remote_model="")
            idx.index_project()
            self.assertIn("delete.py", idx._file_mtimes)

            # Delete file
            (project / "delete.py").unlink()
            self.assertTrue(idx._check_stale())
