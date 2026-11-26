A regression has been introduced into the click library in `/app` (library source under `/app/src/click`). Some behaviour no longer matches what the project's own test suite expects. These tests currently fail:

- `tests.test_termui::test_progressbar_update`
- `tests.test_termui::test_progressbar_update_with_item_show_func`

Find the defect in the library source and fix it. Do not modify the tests: grading uses the original test suite, and every test that passed before the regression must still pass.

Run the test suite from `/app` with `python -m pytest tests`.
