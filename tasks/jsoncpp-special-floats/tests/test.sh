#!/bin/bash
# Builds the agent's library with the pristine upstream test programs and the
# hidden tests, runs every test case individually, then grades.
# Writes /logs/verifier/results.json and /logs/verifier/reward.json.
set -u
mkdir -p /logs/verifier
cd /app
BUILD=/tmp/build
rm -rf "$BUILD" && mkdir -p "$BUILD"
CXX=(g++ -std=c++17 -O1 -Iinclude -Isrc/test_lib_json)

compile() { "${CXX[@]}" -c "$1" -o "$BUILD/$2.o" >> /logs/verifier/build.log 2>&1; }

pids=()
compile src/lib_json/json_reader.cpp json_reader & pids+=($!)
compile src/lib_json/json_value.cpp  json_value  & pids+=($!)
compile src/lib_json/json_writer.cpp json_writer & pids+=($!)
compile src/test_lib_json/main.cpp     test_main  & pids+=($!)
compile src/test_lib_json/jsontest.cpp jsontest   & pids+=($!)
compile src/test_lib_json/fuzz.cpp     fuzz       & pids+=($!)
compile src/jsontestrunner/main.cpp    runner     & pids+=($!)
compile /tests/hidden_tests.cpp        hidden     & pids+=($!)
for pid in "${pids[@]}"; do wait "$pid"; done

LIB=("$BUILD/json_reader.o" "$BUILD/json_value.o" "$BUILD/json_writer.o")
g++ "${LIB[@]}" "$BUILD/test_main.o" "$BUILD/jsontest.o" "$BUILD/fuzz.o" \
  -o "$BUILD/jsoncpp_test" >> /logs/verifier/build.log 2>&1
g++ "${LIB[@]}" "$BUILD/runner.o" -o "$BUILD/jsontestrunner" >> /logs/verifier/build.log 2>&1
g++ "${LIB[@]}" "$BUILD/hidden.o" "$BUILD/jsontest.o" \
  -o "$BUILD/hidden_tests" >> /logs/verifier/build.log 2>&1

python3 /tests/run_tests.py "$BUILD"
python3 /tests/grade.py
