"""Simple metrics/logging for latency, cache hit rate, and tool usage quality."""

from __future__ import annotations

import json
import os
import time
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Optional


TOOL_SAVINGS_FACTOR: dict[str, float] = {
    "smart_read": 0.87,
    "find_symbols": 0.99,
    "semantic_search": 0.96,
    "get_dependencies": 0.96,
    "trace_calls": 0.90,
    "compact_change_intelligence": 0.75,
    "analyze_project": 0.85,
    "code_search": 0.90,
    "find_files": 0.80,
    "dir_summary": 0.80,
}


class Metrics:
    """Collect and report operational metrics."""

    _DEFAULT_EVENTS_DIR = Path.home() / ".code-context-cache" / "metrics"

    def __init__(self, events_path: Optional[Path] = None):
        self._cache_hits = 0
        self._cache_misses = 0
        self._summary_count = 0
        self._summary_latency: list[float] = []
        self._draft_count = 0
        self._draft_acceptances = 0
        self._calls: dict[str, int] = defaultdict(int)
        self._call_latency_ms: dict[str, int] = defaultdict(int)
        self._call_errors: dict[str, int] = defaultdict(int)
        if events_path is not None:
            self._events_path = events_path
        else:
            _test_mode = os.environ.get("CC_TEST_MODE")
            if _test_mode:
                raise RuntimeError(
                    "Metrics() without events_path in CC_TEST_MODE would write to production. "
                    "Pass events_path=Path(tmp)/'events.jsonl' in tests."
                )
            self._events_path = self._DEFAULT_EVENTS_DIR / "events.jsonl"
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

    def record_call(self, tool_name: str, latency_ms: int = 0, ok: bool = True,
                    tokens_input: int = 0, tokens_output: int = 0, tokens_baseline: int = 0,
                    baseline_op: str = ""):
        self._calls[tool_name] += 1
        self._call_latency_ms[tool_name] += max(0, int(latency_ms))
        if not ok:
            self._call_errors[tool_name] += 1

        savings = max(0, tokens_baseline - tokens_input - tokens_output)
        event = {
            "ts": int(time.time()),
            "tool": tool_name,
            "latency_ms": int(latency_ms),
            "ok": bool(ok),
            "tokens_input": int(tokens_input),
            "tokens_output": int(tokens_output),
            "tokens_baseline": int(tokens_baseline),
            "savings_tokens": int(savings),
            "baseline_op": str(baseline_op),
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

    # ── slowest tools ────────────────────────────────────────────────────

    def slowest(self, limit: int = 5) -> list[dict]:
        tools = []
        for name, count in self._calls.items():
            total_latency = self._call_latency_ms.get(name, 0)
            errors = self._call_errors.get(name, 0)
            avg_latency = round(total_latency / count, 1) if count else 0.0
            tools.append({
                "tool": name,
                "calls": count,
                "total_latency_ms": total_latency,
                "avg_latency_ms": avg_latency,
                "errors": errors,
            })
        tools.sort(key=lambda t: t["avg_latency_ms"], reverse=True)
        return tools[:limit]

    def errors_summary(self) -> dict:
        tools_with_errors = []
        total_calls = 0
        total_errors = 0
        for name, count in self._calls.items():
            errs = self._call_errors.get(name, 0)
            total_calls += count
            total_errors += errs
            if errs > 0:
                tools_with_errors.append({
                    "tool": name,
                    "calls": count,
                    "errors": errs,
                })
        error_rate = round(total_errors / total_calls, 4) if total_calls else 0.0
        return {
            "tools_with_errors": tools_with_errors,
            "total_calls": total_calls,
            "total_errors": total_errors,
            "error_rate": error_rate,
        }

    def reset(self) -> str:
        import os
        import shutil

        archive_paths = []

        evts = self._events_path
        if evts.exists():
            bak = evts.with_suffix(".jsonl.bak")
            if bak.exists():
                bak.unlink()
            os.replace(str(evts), str(bak))
            archive_paths.append(str(bak))

        daily = self._daily_dir
        if daily.exists():
            archive_dir = daily / "archive"
            archive_dir.mkdir(parents=True, exist_ok=True)
            for f in sorted(daily.glob("*.json")):
                shutil.move(str(f), str(archive_dir / f.name))
            archive_paths.append(str(archive_dir))

        self._cache_hits = 0
        self._cache_misses = 0
        self._summary_count = 0
        self._summary_latency.clear()
        self._draft_count = 0
        self._draft_acceptances = 0
        self._calls.clear()
        self._call_latency_ms.clear()
        self._call_errors.clear()

        if archive_paths:
            return f"Metrics reset. Archived: {archive_paths[0]}"
        return "Metrics reset. No data to archive."

    def _compute_real_savings_factor(self, tool_name: str) -> float:
        events = self.recent_events(limit=500)
        tool_events = [e for e in events if e.get("tool") == tool_name and e.get("tokens_baseline", 0) > 0 and e.get("savings_tokens") is not None]
        if not tool_events:
            return TOOL_SAVINGS_FACTOR.get(tool_name, 0.50)
        total_factor = sum(e["savings_tokens"] / e["tokens_baseline"] for e in tool_events)
        return round(total_factor / len(tool_events), 2)

    @staticmethod
    def _savings_estimate(tool_name: str, calls: int) -> int:
        factor = TOOL_SAVINGS_FACTOR.get(tool_name, 0.50)
        avg_file_size_tokens = 1500
        return int(calls * avg_file_size_tokens * factor)

    # ── daily snapshot ───────────────────────────────────────────────────

    @property
    def _daily_dir(self) -> Path:
        p = self._events_path.parent / "daily"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def _daily_snapshot(self) -> dict:
        today = date.today().isoformat()
        today_ts_start = int(datetime.strptime(today, "%Y-%m-%d").timestamp())

        tools: dict[str, dict] = {}
        if self._events_path.exists():
            try:
                for line in self._events_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if event.get("ts", 0) < today_ts_start:
                        continue
                    tool_name = event.get("tool", "unknown")
                    if tool_name not in tools:
                        tools[tool_name] = {
                            "calls": 0, "total_latency_ms": 0, "errors": 0,
                            "savings_tokens": 0, "total_baseline": 0, "total_output": 0,
                            "is_estimate": False,
                        }
                    tools[tool_name]["calls"] += 1
                    tools[tool_name]["total_latency_ms"] += event.get("latency_ms", 0)
                    if not event.get("ok", True):
                        tools[tool_name]["errors"] += 1

                    savings_tokens = event.get("savings_tokens")
                    if savings_tokens is not None:
                        tools[tool_name]["savings_tokens"] += savings_tokens
                        tools[tool_name]["total_baseline"] += event.get("tokens_baseline", 0)
                        tools[tool_name]["total_output"] += event.get("tokens_output", 0)
                    else:
                        tools[tool_name]["is_estimate"] = True
                        tools[tool_name]["savings_tokens"] += self._savings_estimate(tool_name, 1)
            except OSError:
                pass

        total_savings = 0
        for tname, tstats in tools.items():
            tstats["avg_latency_ms"] = round(tstats["total_latency_ms"] / tstats["calls"], 1) if tstats["calls"] else 0.0
            savings = tstats["savings_tokens"]
            total_savings += savings
            tstats["est_saved_tokens"] = savings
            del tstats["total_latency_ms"]

        snapshot = {
            "date": today,
            "tools": tools,
            "total_savings_estimate_tokens": total_savings,
            "total_savings_tokens": total_savings,
        }

        daily_file = self._daily_dir / f"{today}.json"
        tmp = daily_file.with_suffix(".tmp")
        try:
            tmp.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
            os.replace(str(tmp), str(daily_file))
        except OSError:
            pass

        return snapshot

    def get_daily_trend(self, days: int = 7) -> list[dict]:
        today = date.today()
        results = []
        for i in range(days):
            day = date.fromordinal(today.toordinal() - i)
            daily_file = self._daily_dir / f"{day.isoformat()}.json"
            if daily_file.exists():
                try:
                    data = json.loads(daily_file.read_text(encoding="utf-8"))
                    results.append(data)
                except (OSError, json.JSONDecodeError):
                    results.append({"date": day.isoformat(), "error": "corrupt file"})
            else:
                results.append({"date": day.isoformat(), "tools": {}, "total_savings_estimate_tokens": 0})
        return results

    # ── report ───────────────────────────────────────────────────────────

    def report(self) -> str:
        events = self.recent_events(limit=200)
        real_events = [e for e in events if e.get("savings_tokens") is not None]
        est_events = [e for e in events if e.get("savings_tokens") is None]

        real_savings = sum(e["savings_tokens"] for e in real_events)
        total_baseline = sum(e.get("tokens_baseline", 0) for e in real_events)
        total_output = sum(e.get("tokens_output", 0) for e in real_events)
        real_count = len(real_events)
        avg_savings = round(real_savings / real_count, 1) if real_count else 0.0

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

        lines.append("  Token savings:")
        lines.append(f"    Real (last {real_count} events): {real_savings:,} tokens saved, avg {avg_savings:,}/call")
        if total_baseline > 0:
            lines.append(f"    Total baseline: {total_baseline:,}, output: {total_output:,}")
            lines.append(f"    Savings rate: {real_savings / total_baseline * 100:.1f}%")
        if est_events:
            est_total = sum(self._savings_estimate(e["tool"], 1) for e in est_events)
            lines.append(f"    Estimated (old events): {est_total:,} tokens")

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
