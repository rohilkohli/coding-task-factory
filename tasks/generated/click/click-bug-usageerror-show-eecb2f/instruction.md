A regression has been introduced into the click library in `/app` (library source under `/app/src/click`). Some behaviour no longer matches what the project's own test suite expects. These tests currently fail:

- `tests.test_basic::test_string_option[args2-Error: Option '--s' requires an argument.]`
- `tests.test_formatting::test_formatting_usage_custom_help`
- `tests.test_formatting::test_formatting_usage_error`
- `tests.test_formatting::test_formatting_usage_error_help_hint[help_names0-extra_options0-Try 'cli foo --help' for help.]`
- `tests.test_formatting::test_formatting_usage_error_help_hint[help_names1-extra_options1-Try 'cli foo --help' for help.]`
- ... and 32 more

Find the defect in the library source and fix it. Do not modify the tests: grading uses the original test suite, and every test that passed before the regression must still pass.

Run the test suite from `/app` with `python -m pytest tests`.
