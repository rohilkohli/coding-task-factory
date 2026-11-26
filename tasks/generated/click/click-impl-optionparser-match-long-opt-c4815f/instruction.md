In the click library in `/app`, the implementation of `_OptionParser._match_long_opt` in `src/click/parser.py` has been removed. Its body is now a stub that fails with "not implemented". Re-implement it so it behaves the way the rest of the codebase and its documentation expect.

Current signature and documentation:

```python
def _match_long_opt(
        self, opt: str, explicit_value: str | None, state: _ParsingState
    ) -> None:
```

The project's test suite exercises this code. These tests currently fail:

- `tests.test_arguments::test_argument_help`
- `tests.test_arguments::test_argument_help_deprecated_without_help_lists_all`
- `tests.test_arguments::test_argument_help_empty_string_lists_all`
- `tests.test_arguments::test_argument_help_lists_undocumented_arguments`
- `tests.test_arguments::test_argument_help_optional_metavar`
- ... and 453 more

Make them pass without modifying any tests, and keep the rest of the test suite passing.

Run the test suite from `/app` with `python -m pytest tests`.
