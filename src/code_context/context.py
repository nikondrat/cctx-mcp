"""Shared server context — threading local for token baseline tracking."""

import threading
import time
import functools
from typing import Any, Optional

from code_context.metrics import get_metrics

_tool_token_ctx = threading.local()


def set_tool_baseline(baseline: int = 0, baseline_op: str = ""):
    _tool_token_ctx.baseline = baseline
    _tool_token_ctx.baseline_op = baseline_op


def _result_ok(result: Any) -> bool:
    if isinstance(result, str):
        lowered = result.lower().strip()
        if lowered.startswith("error:") or lowered.startswith("err:"):
            return False
        if " unavailable" in lowered:
            return False
        if " failed" in lowered:
            return False
        if "not found" in lowered or "no matches" in lowered:
            return False
    return True


def instrument_tool(tool_name: str):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            started = time.perf_counter()
            ok = True
            result = None
            try:
                result = func(*args, **kwargs)
                ok = _result_ok(result)
                return result
            except Exception:
                ok = False
                raise
            finally:
                latency_ms = int((time.perf_counter() - started) * 1000)
                tokens_output = 0
                if result is not None and isinstance(result, str):
                    tokens_output = max(1, len(result) // 4)
                get_metrics().record_call(
                    tool_name,
                    latency_ms=latency_ms,
                    ok=ok,
                    tokens_input=getattr(_tool_token_ctx, 'input', 0),
                    tokens_output=tokens_output,
                    tokens_baseline=getattr(_tool_token_ctx, 'baseline', 0),
                    baseline_op=getattr(_tool_token_ctx, 'baseline_op', ''),
                )

        return wrapper

    return decorator
