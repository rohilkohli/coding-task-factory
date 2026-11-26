A regression has been introduced into the JsonCpp library in `/app` (library source under `/app/src/lib_json`). Some behaviour no longer matches what the project's own test suite expects. These tests currently fail:

- `data/fail_test_control_char_01.json [BuiltStyledStreamWriter]`
- `data/fail_test_control_char_01.json [StyledStreamWriter]`
- `data/fail_test_control_char_01.json [StyledWriter]`
- `unit/CharReaderTest/parseString`
- `unit/CharReaderTest/parseWithDetailError`

Find the defect in the library source and fix it. Do not modify the tests: grading uses the original test suite, and every test that passed before the regression must still pass.

CMake is not installed; build and run the unit tests with:

```bash
mkdir -p /tmp/b && g++ -std=c++17 -O1 -Iinclude -Isrc/test_lib_json src/lib_json/*.cpp src/test_lib_json/{main,jsontest,fuzz}.cpp -o /tmp/b/jsoncpp_test && /tmp/b/jsoncpp_test
```

Data-driven tests: build `src/jsontestrunner/main.cpp` with the library as `/tmp/b/jsontestrunner` and run `python3 test/runjsontests.py /tmp/b/jsontestrunner test/data`.
