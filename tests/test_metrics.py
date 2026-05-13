"""Unit tests for Metrics reporting and event persistence."""

import json
import os
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

from code_context.metrics import Metrics, TOOL_SAVINGS_FACTOR


class TestMetrics(unittest.TestCase):
    def test_record_call_updates_report_and_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            metrics = Metrics()
            metrics._events_path = Path(tmp) / "events.jsonl"

            metrics.record_call("smart_read", latency_ms=12, ok=True)
            metrics.record_call("code_search", latency_ms=25, ok=False)

            report = metrics.report()
            self.assertIn("smart_read: 1 calls", report)
            self.assertIn("code_search: 1 calls", report)
            self.assertIn("errors 1", report)

            events = metrics.recent_events(limit=10)
            self.assertEqual(len(events), 2)
            self.assertEqual(events[0]["tool"], "smart_read")
            self.assertEqual(events[1]["tool"], "code_search")

    def test_hints_detect_missing_semantic_usage(self):
        with tempfile.TemporaryDirectory() as tmp:
            metrics = Metrics()
            metrics._events_path = Path(tmp) / "events.jsonl"

            for _ in range(3):
                metrics.record_call("code_search", latency_ms=10, ok=True)

            report = metrics.report()
            self.assertIn("Use semantic_search first", report)

    def test_slowest_returns_tools_sorted_by_latency(self):
        metrics = Metrics()
        metrics.record_call("alpha", latency_ms=10, ok=True)
        metrics.record_call("alpha", latency_ms=20, ok=True)
        metrics.record_call("beta", latency_ms=100, ok=True)

        result = metrics.slowest(limit=5)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["tool"], "beta")
        self.assertEqual(result[0]["avg_latency_ms"], 100.0)
        self.assertEqual(result[1]["tool"], "alpha")
        self.assertEqual(result[1]["avg_latency_ms"], 15.0)

    def test_slowest_respects_limit(self):
        metrics = Metrics()
        metrics.record_call("a", latency_ms=10, ok=True)
        metrics.record_call("b", latency_ms=20, ok=True)
        metrics.record_call("c", latency_ms=30, ok=True)

        result = metrics.slowest(limit=2)
        self.assertEqual(len(result), 2)

    def test_slowest_returns_empty_list_when_no_calls(self):
        metrics = Metrics()
        self.assertEqual(metrics.slowest(), [])

    def test_errors_summary_returns_tools_with_errors(self):
        metrics = Metrics()
        metrics.record_call("ok_tool", latency_ms=10, ok=True)
        metrics.record_call("bad_tool", latency_ms=50, ok=False)
        metrics.record_call("bad_tool", latency_ms=30, ok=False)

        summary = metrics.errors_summary()
        self.assertEqual(len(summary["tools_with_errors"]), 1)
        self.assertEqual(summary["tools_with_errors"][0]["tool"], "bad_tool")
        self.assertEqual(summary["tools_with_errors"][0]["errors"], 2)
        self.assertEqual(summary["total_calls"], 3)
        self.assertEqual(summary["total_errors"], 2)

    def test_errors_summary_returns_no_errors(self):
        metrics = Metrics()
        metrics.record_call("good", latency_ms=10, ok=True)
        summary = metrics.errors_summary()
        self.assertEqual(summary["tools_with_errors"], [])
        self.assertEqual(summary["error_rate"], 0.0)

    def test_savings_estimate_uses_correct_factor(self):
        smart_read_savings = Metrics._savings_estimate("smart_read", 5)
        self.assertEqual(smart_read_savings, int(5 * 1500 * TOOL_SAVINGS_FACTOR["smart_read"]))

        unknown_savings = Metrics._savings_estimate("nonexistent", 10)
        self.assertEqual(unknown_savings, int(10 * 1500 * 0.50))

    def test_daily_snapshot_creates_file_with_todays_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            metrics = Metrics()
            metrics._events_path = Path(tmp) / "events.jsonl"

            today = date.today().isoformat()
            ts = int(datetime.strptime(today, "%Y-%m-%d").timestamp())
            events = [
                {"ts": ts, "tool": "smart_read", "latency_ms": 12, "ok": True},
                {"ts": ts, "tool": "find_symbols", "latency_ms": 5, "ok": True},
                {"ts": ts, "tool": "code_search", "latency_ms": 30, "ok": False},
            ]
            metrics._events_path.write_text(
                "\n".join(json.dumps(e) for e in events), encoding="utf-8"
            )

            snapshot = metrics._daily_snapshot()
            self.assertEqual(snapshot["date"], today)
            self.assertIn("smart_read", snapshot["tools"])
            self.assertIn("find_symbols", snapshot["tools"])
            self.assertIn("code_search", snapshot["tools"])
            self.assertGreater(snapshot["total_savings_estimate_tokens"], 0)

            daily_file = metrics._daily_dir / f"{today}.json"
            self.assertTrue(daily_file.exists())
            loaded = json.loads(daily_file.read_text(encoding="utf-8"))
            self.assertEqual(loaded["date"], today)

    def test_get_daily_trend_returns_recent_days(self):
        with tempfile.TemporaryDirectory() as tmp:
            metrics = Metrics()
            daily_dir = Path(tmp) / "daily"
            daily_dir.mkdir(parents=True, exist_ok=True)
            metrics._events_path = Path(tmp) / "events.jsonl"
            metrics._events_path.touch()

            today = date.today()
            snapshot = {
                "date": today.isoformat(),
                "tools": {"smart_read": {"calls": 3, "errors": 0}},
                "total_savings_estimate_tokens": 5000,
            }
            (daily_dir / f"{today.isoformat()}.json").write_text(json.dumps(snapshot), encoding="utf-8")

            trend = metrics.get_daily_trend(days=3)
            self.assertEqual(len(trend), 3)
            self.assertEqual(trend[0]["date"], today.isoformat())
            self.assertIn("smart_read", trend[0]["tools"])
            self.assertEqual(trend[1].get("tools"), {})  # no data
