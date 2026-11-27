#!/bin/bash
# Grades the agent's regression test (/app/regression/test_regression.py) by
# running it against the reference, the defective and the hidden wrong
# implementations. Writes /logs/verifier/results.json and reward.json.
set -u
mkdir -p /logs/verifier
python3 /tests/run_variants.py --test /app/regression/test_regression.py \
  --variants /tests/variants --config /tests/rigor.json --out /logs/verifier
