# Validation summary

| Task | Language | Difficulty | Feature tests (F2P) | Regression tests (P2P) | Flaky | Oracle (Harbor) | No-op (Harbor) | Wrong solutions rejected | Upstream tests alone |
|---|---|---|---|---|---|---|---|---|---|
| click-datetime-type | python | easy | 58 | 2563 | 0 | 1, 1, 1 | 0 | 14/14 | 9/14 |
| jsoncpp-special-floats | cpp | medium | 11 | 342 | 0 | 1, 1, 1 | 0 | 14/14 | 11/14 |
| zod-iban-format | typescript | medium | 56 | 5519 | 0 | 1, 1, 1 | 0 | 14/14 | 9/14 |

**Wrong solutions rejected overall: 42/42** (upstream tests alone: 29/42).

Feature tests count each test case as the harness reports it; zod's vitest reports runtime and type-level checks separately, and click's F2P includes the whole `tests/test_info_dict.py` module, which cannot load without `click.DateTime`.
