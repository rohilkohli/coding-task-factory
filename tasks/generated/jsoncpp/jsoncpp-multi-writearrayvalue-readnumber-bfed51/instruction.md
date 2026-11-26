Several regressions (2) have been introduced into the JsonCpp library in `/app` (library source under `/app/src/lib_json`). They are independent defects in different parts of the library. These tests currently fail:

- `data/legacy_test_array_02.json [BuiltStyledStreamWriter]`
- `data/legacy_test_array_02.json [StyledStreamWriter]`
- `data/legacy_test_array_02.json [StyledWriter]`
- `data/legacy_test_array_03.json [BuiltStyledStreamWriter]`
- `data/legacy_test_array_03.json [StyledStreamWriter]`
- ... and 73 more

Find and fix every defect in the library source. Fixing only some of them is not enough: all of the tests above must pass. Do not modify the tests; grading uses the original test suite, and every test that passed before the regressions must still pass.

CMake is not installed; build and run the unit tests with:

```bash
mkdir -p /tmp/b && g++ -std=c++17 -O1 -Iinclude -Isrc/test_lib_json src/lib_json/*.cpp src/test_lib_json/{main,jsontest,fuzz}.cpp -o /tmp/b/jsoncpp_test && /tmp/b/jsoncpp_test
```

Data-driven tests: build `src/jsontestrunner/main.cpp` with the library as `/tmp/b/jsontestrunner` and run `python3 test/runjsontests.py /tmp/b/jsontestrunner test/data`.
