A regression has been introduced into the click library in `/app` (library source under `/app/src/click`). Some behaviour no longer matches what the project's own test suite expects. These tests currently fail:

- `tests.test_basic::test_basic_group`
- `tests.test_basic::test_summary_line`
- `tests.test_commands::test_auto_shorthelp`
- `tests.test_commands::test_deprecated_help_text_is_not_translated`
- `tests.test_shell_completion::test_full_complete[fish-env4-plain,a\nplain,b\tbee\n]`
- ... and 26 more

Find the defect in the library source and fix it. Do not modify the tests: grading uses the original test suite, and every test that passed before the regression must still pass.

Run the test suite from `/app` with `python -m pytest tests`.
