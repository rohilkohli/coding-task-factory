A regression has been introduced into the click library in `/app` (library source under `/app/src/click`). Some behaviour no longer matches what the project's own test suite expects. These tests currently fail:

- `tests.test_arguments::test_good_defaults_for_nargs[argument_params9-args9-expected9]`
- `tests.test_arguments::test_nargs_specified_plus_star_ordering`
- `tests.test_arguments::test_nargs_tup`
- `tests.test_arguments::test_nargs_tup_composite[opts0]`
- `tests.test_arguments::test_nargs_tup_composite[opts1]`
- ... and 3 more

Find the defect in the library source and fix it. Do not modify the tests: grading uses the original test suite, and every test that passed before the regression must still pass.

Run the test suite from `/app` with `python -m pytest tests`.
