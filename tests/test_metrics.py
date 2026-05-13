"""Unit tests for Metrics reporting and event persistence."""

import tempfile
import unittest
from pathlib import Path

from metrics import Metrics


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
