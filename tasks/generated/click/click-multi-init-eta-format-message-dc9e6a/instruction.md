Several regressions (3) have been introduced into the click library in `/app` (library source under `/app/src/click`). They are independent defects in different parts of the library. These tests currently fail:

- `tests.test_arguments::test_argument_help_deprecated_without_help_lists_all`
- `tests.test_arguments::test_argument_help_empty_string_lists_all`
- `tests.test_arguments::test_argument_help_lists_undocumented_arguments`
- `tests.test_arguments::test_bad_defaults_for_nargs[Sentinel.UNSET-Error: Missing argument 'A...'.]`
- `tests.test_arguments::test_empty_nargs`
- ... and 41 more

Find and fix every defect in the library source. Fixing only some of them is not enough: all of the tests above must pass. Do not modify the tests; grading uses the original test suite, and every test that passed before the regressions must still pass.

Run the test suite from `/app` with `python -m pytest tests`.
