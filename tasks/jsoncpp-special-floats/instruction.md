The JsonCpp library in `/app` can already *write* `NaN` and infinities when `StreamWriterBuilder`'s `useSpecialFloats` setting is on, but the reader cannot read them back. Please add a `CharReaderBuilder` setting that lets the reader accept them.

**The setting:**
- Name it `"allowSpecialFloats"` (boolean). `CharReaderBuilder::setDefaults()`, `CharReaderBuilder::strictMode()` and `CharReaderBuilder::ecma404Mode()` must all set it to `false`. `CharReaderBuilder::validate()` must accept the key, and it must still reject unknown keys.
- Document it in the list of `CharReaderBuilder` settings in `include/json/reader.h`.

**When the setting is `true`:**
- The reader accepts the exact, case-sensitive tokens `NaN`, `Infinity`, `-Infinity` and `+Infinity` anywhere a JSON value can appear: object members, array elements, and the top-level value.
- They become `double` values: a quiet NaN, positive infinity, negative infinity and positive infinity respectively.
- Like every other value, they record source offsets. `getOffsetStart()` and `getOffsetLimit()` span the token text, including the sign.
- Anything that isn't exactly one of those tokens is still a parse error. That includes `nan`, `NAN`, `Inf`, `-Inf`, `Infinit`, `NaNa`, `- Infinity` (with a space), `--Infinity`, `1Infinity`, `.Infinity` and `-NaN`.
- Ordinary numbers, including negative numbers and exponents, parse exactly as before. The setting must also combine with the other reader settings (comments, trailing commas, and so on).

**When the setting is `false` (the default):**
- Nothing changes. The special tokens are rejected. For example, `{"a": NaN}` fails with `* Line 1, Column 7` / `Syntax error: value, object or array expected.`

The reader implementation is in `src/lib_json/json_reader.cpp`. CMake isn't installed, so build and run the unit tests with g++ directly:

```bash
mkdir -p /tmp/b && g++ -std=c++17 -O1 -Iinclude -Isrc/test_lib_json src/lib_json/*.cpp src/test_lib_json/{main,jsontest,fuzz}.cpp -o /tmp/b/jsoncpp_test && /tmp/b/jsoncpp_test
```

The data-driven tests need the `jsontestrunner` program built from `src/jsontestrunner/main.cpp` plus the library. Run them with `python3 test/runjsontests.py /tmp/b/jsontestrunner test/data`.
