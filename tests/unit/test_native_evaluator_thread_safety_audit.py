from __future__ import annotations

from pathlib import Path


def test_native_evaluator_cache_is_explicitly_synchronized() -> None:
    source = Path("src/native/include/evaluators.hpp").read_text(encoding="utf-8")

    assert "mutable std::mutex cache_mutex;" in source
    assert "std::lock_guard<std::mutex> lock(cache_mutex);" in source
    assert "for (int i = 0; i < 6; ++i) last_result[i] = result[i];" in source
    assert "last_jd = jd;" in source
