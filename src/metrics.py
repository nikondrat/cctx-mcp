"""Simple metrics/logging for latency, cache hit rate, and tool usage quality."""

from __future__ import annotations

import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Optional


class Metrics:
    """Collect and report operational metrics."""

    def __init__(self):
        self._cache_hits = 0
        self._cache_misses = 0
        self._summary_count = 0
        self._summary_latency: list[float] = []
        self._draft_count = 0
        self._draft_acceptances = 0
        self._calls: dict[str, int] = defaultdict(int)
        self._call_latency_ms: dict[str, int] = defaultdict(int)
        self._call_errors: dict[str, int] = defaultdict(int)
        self._events_path = Path.home() / ".code-context-cache" / "metrics" / "events.jsonl"
        self._events_path.parent.mkdir(parents=True, exist_ok=True)

    # ── cache ────────────────────────────────────────────────────────────

    def record_cache_hit(self):
        self._cache_hits += 1

    def record_cache_miss(self):
        self._cache_misses += 1

    @property
    def cache_hit_rate(self) -> float:
        total = self._cache_hits + self._cache_misses
        if total == 0:
            return 0.0
        return round(self._cache_hits / total, 3)

    # ── summaries ────────────────────────────────────────────────────────

    def record_summary(self, latency_ms: float):
        self._summary_count += 1
        self._summary_latency.append(latency_ms)

    @property
    def avg_summary_latency_ms(self) -> float:
        if not self._summary_latency:
            return 0.0
        return round(sum(self._summary_latency) / len(self._summary_latency), 1)

    # ── drafts ───────────────────────────────────────────────────────────

    def record_draft(self):
        self._draft_count += 1

    def record_draft_acceptance(self):
        self._draft_acceptances += 1

    @property
    def draft_acceptance_rate(self) -> float:
        if self._draft_count == 0:
            return 0.0
        return round(self._draft_acceptances / self._draft_count, 3)

    # ── tool calls ───────────────────────────────────────────────────────

    def record_call(self, tool_name: str, latency_ms: int = 0, ok: bool = True):
        self._calls[tool_name] += 1
        self._call_latency_ms[tool_name] += max(0, int(latency_ms))
        if not ok:
            self._call_errors[tool_name] += 1

        event = {
            "ts": int(time.time()),
            "tool": tool_name,
            "latency_ms": int(latency_ms),
            "ok": bool(ok),
        }
        try:
            with self._events_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event) + "\n")
        except OSError:
            # Metrics must never break tool execution.
            pass

    def recent_events(self, limit: int = 25) -> list[dict]:
        if limit <= 0:
            return []
        if not self._events_path.exists():
            return []

        try:
            lines = self._events_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []

        events: list[dict] = []
        for line in lines[-limit:]:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return events

    def _hints(self) -> list[str]:
        hints: list[str] = []
        smart_reads = self._calls.get("smart_read", 0)
        code_searches = self._calls.get("code_search", 0)
        semantic_searches = self._calls.get("semantic_search", 0)
        symbol_searches = self._calls.get("find_symbols", 0)

        if code_searches >= 3 and semantic_searches == 0:
            hints.append("Use semantic_search first for natural-language queries before code_search.")
        if smart_reads == 0 and (code_searches > 0 or symbol_searches > 0):
            hints.append("Use smart_read before raw file reads to reduce token usage.")
        if self._calls.get("compact_change_intelligence", 0) == 0 and self._calls.get("draft_commit", 0) > 0:
            hints.append("Run compact_change_intelligence before draft_commit for lower-token commit context.")
        if not hints:
            hints.append("No obvious usage anti-patterns detected.")
        return hints

    # ── report ───────────────────────────────────────────────────────────

    def report(self) -> str:
        lines = [
            "Metrics Report:",
            f"  Cache hit rate: {self._cache_hits}h/{self._cache_misses}m ({self.cache_hit_rate})",
            f"  Summaries generated: {self._summary_count}",
            f"  Avg summary latency: {self.avg_summary_latency_ms}ms",
            f"  Drafts: {self._draft_count}, acceptance: {self.draft_acceptance_rate}",
            "  Tool calls:",
        ]
        for name, count in sorted(self._calls.items(), key=lambda x: x[1], reverse=True):
            avg = self._call_latency_ms[name] / count if count else 0
            errs = self._call_errors.get(name, 0)
            lines.append(f"    {name}: {count} calls, avg {avg:.1f}ms, errors {errs}")

        lines.append("  Hints:")
        for hint in self._hints():
            lines.append(f"    - {hint}")

        lines.append(f"  Events log: {self._events_path}")
        return "\n".join(lines)


# Singleton
_metrics: Optional[Metrics] = None


def get_metrics() -> Metrics:
    global _metrics
    if _metrics is None:
        _metrics = Metrics()
    return _metrics
