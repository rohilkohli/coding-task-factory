In the JsonCpp library in `/app`, the implementation of `Path::resolve` in `src/lib_json/json_value.cpp` has been removed. Its body is now a stub that fails with "not implemented". Re-implement it so it behaves the way the rest of the codebase and its documentation expect.

Current signature and documentation:

```cpp
Value Path::resolve(const Value& root, const Value& defaultValue) const { ... }
```

The project's test suite exercises this code. These tests currently fail:

- `unit/ValueTest/searchValueByPath`

Make them pass without modifying any tests, and keep the rest of the test suite passing.

CMake is not installed; build and run the unit tests with:

```bash
mkdir -p /tmp/b && g++ -std=c++17 -O1 -Iinclude -Isrc/test_lib_json src/lib_json/*.cpp src/test_lib_json/{main,jsontest,fuzz}.cpp -o /tmp/b/jsoncpp_test && /tmp/b/jsoncpp_test
```

Data-driven tests: build `src/jsontestrunner/main.cpp` with the library as `/tmp/b/jsontestrunner` and run `python3 test/runjsontests.py /tmp/b/jsontestrunner test/data`.
