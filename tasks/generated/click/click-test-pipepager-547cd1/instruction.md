A defect has been introduced into `_pipepager` in `src/click/_termui_impl.py` of the click library in `/app`. The project's tests that would have caught it have been removed. Your job is **not** to fix the defect, but to write a regression test that exposes it.

Create `/app/regression/test_regression.py` (pytest) with one or more tests that:

1. **fail** on the current code, because of the defect, and
2. **pass** once `_pipepager` behaves correctly again.

Grading runs your test file against the correct implementation, the current defective one, and 6 other plausible-but-wrong implementations of the same code that you cannot see. Your tests earn credit only if they pass on the correct implementation, fail on the defective one, **and** fail on at least 75% of the wrong implementations. Pin down the intended behaviour precisely; assertions about the source text rather than behaviour will not meet the bar. Do not modify the library source, which is ignored for grading.

Your file is run from `/app/tests/` during grading, so the fixtures in `tests/conftest.py` (for example `runner`) are available. To try it locally: `cp /app/regression/test_regression.py /app/tests/ && cd /app && python -m pytest tests/test_regression.py`.
