The `click` library in `/app` (source in `/app/src/click`) is missing its `DateTime` parameter type. Command-line tools built with it need to accept dates and times as option and argument values. Please add it.

Add a parameter type class `DateTime`, importable as both `click.DateTime` and `click.types.DateTime`, that converts string values into `datetime.datetime` objects. It should behave like this:

- **Formats.** `DateTime(formats=None)` takes a list or tuple of `datetime.strptime` format strings and stores it on the `formats` attribute. When `formats` is not given, use these defaults, in this order: `"%Y-%m-%d"`, `"%Y-%m-%dT%H:%M:%S"`, `"%Y-%m-%d %H:%M:%S"`.
- **Parsing.** Try each format in order and return the result of the first one that parses. If the value is already a `datetime.datetime`, return it unchanged.
- **Errors.** If no format matches, fail the parameter the normal click way, so the command exits with a usage error (exit code 2). Use exactly this message: `'<value>' does not match the formats '<fmt1>', '<fmt2>', '<fmt3>'.` The value and each format are shown with `repr()` quoting, and the formats are separated by `, `. When there is exactly one format, use the singular wording instead: `'<value>' does not match the format '<fmt1>'.`
- **Help text.** The metavar is the formats joined by `|` inside square brackets. For example, `--start_date [%Y-%m-%d|%Y-%m-%dT%H:%M:%S|%Y-%m-%d %H:%M:%S]`, and an optional argument shows in the usage line as `[%Y-%m-%d]`, not `[[%Y-%m-%d]]`.
- **Introspection.** The type's `name` is `"datetime"` and `repr()` returns `"DateTime"`. `to_info_dict()` returns the standard parameter-type keys plus `"formats"`.

Keep the change consistent with the style of the existing parameter types in `src/click/types.py`, and don't break the existing behaviour of the library. You can run the test suite from `/app` with `python -m pytest tests`.
