"""Tests for semantic summary generation, provenance, and fallback."""

import tempfile
from pathlib import Path

from code_context.analyzers.base import SemanticSummary, Symbol
from code_context.summaries import SemanticSummarizer


def make_cache():
    from code_context.cache import Cache
    return Cache(cache_dir=Path(tempfile.mkdtemp()))


def test_summary_presence():
    cache = make_cache()
    summarizer = SemanticSummarizer(cache)

    sym = Symbol(name="fetchUser", type="function", start_line=1, end_line=10,
                 doc_comment="Fetch a user by ID from the database",
                 parameters="user_id: int", return_type="User?")
    file_hash = "abc123"
    summary = summarizer.summarize_symbol(sym, file_hash, ["db", "models"])
    ss = summary.to_dict()

    assert ss["summary_text"]
    assert "Fetch" in ss["summary_text"] or "fetch" in ss["summary_text"]
    assert ss["source"] == "doc"  # doc comment available → source=doc
    assert ss["confidence"] == 0.8


def test_provenance_fields():
    cache = make_cache()
    summarizer = SemanticSummarizer(cache)

    sym = Symbol(name="calculateTotal", type="function", start_line=1, end_line=5,
                 doc_comment="Calculate the total price including tax")
    file_hash = "def456"
    summary = summarizer.summarize_symbol(sym, file_hash, ["pricing"])
    sd = summary.to_dict()

    assert "source" in sd
    assert "confidence" in sd
    assert "last_updated" in sd
    assert sd["source"] == "doc"


def test_fallback_to_heuristic():
    cache = make_cache()
    summarizer = SemanticSummarizer(cache)

    sym = Symbol(name="doSomething", type="function", start_line=1, end_line=3)
    file_hash = "789ghi"
    summary = summarizer.summarize_symbol(sym, file_hash, [])
    sd = summary.to_dict()

    assert sd["source"] == "heuristic"
    assert sd["confidence"] == 0.5  # function with no doc → heuristic


def test_fallback_no_doc():
    cache = make_cache()
    summarizer = SemanticSummarizer(cache)

    sym = Symbol(name="x", type="variable", start_line=1, end_line=1)
    file_hash = "aaa"
    summary = summarizer.summarize_symbol(sym, file_hash, [])
    sd = summary.to_dict()

    assert sd["source"] == "heuristic"
    assert sd["confidence"] == 0.2  # unknown type → low confidence


def test_class_summary_with_children():
    cache = make_cache()
    summarizer = SemanticSummarizer(cache)

    child1 = Symbol(name="get", type="method", start_line=2, end_line=4)
    child2 = Symbol(name="post", type="method", start_line=5, end_line=7)
    sym = Symbol(name="ApiClient", type="class", start_line=1, end_line=7,
                 children=[child1, child2])
    file_hash = "bbb"
    summary = summarizer.summarize_symbol(sym, file_hash, ["http"])
    sd = summary.to_dict()

    assert sd["source"] == "heuristic"
    assert "ApiClient" in sd["behavior"]
    assert "methods" in sd["behavior"]
    assert "get" in sd["behavior"] or "post" in sd["behavior"]


def test_summary_cached_reused():
    cache = make_cache()
    summarizer = SemanticSummarizer(cache)

    sym = Symbol(name="parseInput", type="function", start_line=1, end_line=5,
                 doc_comment="Parse user input string")
    file_hash = "ccc"
    s1 = summarizer.summarize_symbol(sym, file_hash, [])
    s2 = summarizer.summarize_symbol(sym, file_hash, [])
    d1 = {k: v for k, v in s1.to_dict().items() if k != "last_updated"}
    d2 = {k: v for k, v in s2.to_dict().items() if k != "last_updated"}
    assert d1 == d2
