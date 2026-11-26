Several regressions (2) have been introduced into the click library in `/app` (library source under `/app/src/click`). They are independent defects in different parts of the library. These tests currently fail:

- `tests.test_shell_completion::test_choice_conflicting_prefix`
- `tests.test_shell_completion::test_command`
- `tests.test_shell_completion::test_double_dash`
- `tests.test_shell_completion::test_group`
- `tests.test_shell_completion::test_group_command_same_option`
- ... and 28 more

Find and fix every defect in the library source. Fixing only some of them is not enough: all of the tests above must pass. Do not modify the tests; grading uses the original test suite, and every test that passed before the regressions must still pass.

Run the test suite from `/app` with `python -m pytest tests`.
