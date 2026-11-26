#!/bin/bash
# Reference solution: restore upstream allowSpecialFloats reader support
# (open-source-parsers/jsoncpp @ 93acc7b155048f1a66c43235cc205519f1e7a6ea).
set -euo pipefail
cp /solution/files/src/lib_json/json_reader.cpp /app/src/lib_json/json_reader.cpp
cp /solution/files/include/json/reader.h /app/include/json/reader.h
