In the click library in `/app`, the implementation of `_build_prompt` in `src/click/termui.py` has been removed. Its body is now a stub that fails with "not implemented". Re-implement it so it behaves the way the rest of the codebase and its documentation expect.

Current signature and documentation:

```python
def _build_prompt(
    text: str,
    suffix: str,
    show_default: bool | str = False,
    default: object | None = None,
    show_choices: bool = True,
    type: object | None = None,
) -> str:
```

The project's test suite exercises this code. These tests currently fail:

- `tests.test_abort_interrupt::test_interrupt_while_reporting_abort[prompt-1]`
- `tests.test_abort_interrupt::test_interrupt_while_reporting_abort[prompt-None]`
- `tests.test_options::test_callback_validates_prompt`
- `tests.test_options::test_string_show_default_shows_custom_string_in_prompt`
- `tests.test_stream_lifecycle::test_invoke_with_logger_and_prompt`
- ... and 112 more

Make them pass without modifying any tests, and keep the rest of the test suite passing.

Run the test suite from `/app` with `python -m pytest tests`.
