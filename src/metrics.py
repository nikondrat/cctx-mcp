"""Simple metrics/logging for latency, cache hit rate, token reduction, and draft acceptance."""

import time
from collections import defaultdict
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

    def record_call(self, tool_name: str):
        self._calls[tool_name] += 1

    # ── report ───────────────────────────────────────────────────────────

    def report(self) -> str:
        lines = [
            "Metrics Report:",
            f"  Cache hit rate: {self._cache_hits}h/{self._cache_misses}m ({self.cache_hit_rate})",
            f"  Summaries generated: {self._summary_count}",
            f"  Avg summary latency: {self.avg_summary_latency_ms}ms",
            f"  Drafts: {self._draft_count}, acceptance: {self.draft_acceptance_rate}",
            f"  Tool calls:",
        ]
        for name, count in sorted(self._calls.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"    {name}: {count}")
        return "\n".join(lines)


# Singleton
_metrics: Optional[Metrics] = None


def get_metrics() -> Metrics:
    global _metrics
    if _metrics is None:
        _metrics = Metrics()
    return _metrics
