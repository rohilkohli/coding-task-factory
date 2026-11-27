#!/bin/bash
# Reference solution: the upstream tests for this behaviour, as one regression file
# (https://github.com/pallets/click @ 08b803cf32ceb2ae6a772c62d5da42757a897d44).
set -euo pipefail
mkdir -p /app/regression
cp /solution/files/regression/test_regression.py /app/regression/test_regression.py
