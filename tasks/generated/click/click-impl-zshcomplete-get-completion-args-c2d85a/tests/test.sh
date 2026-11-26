#!/bin/bash
# Grades the agent's /app/src with the pristine upstream test suite. Writes /logs/verifier/results.json and reward.json.
set -u
mkdir -p /logs/verifier
cd /app
python -m pytest -p no:cacheprovider -q -rA tests \
  -c /app/pyproject.toml --rootdir=/app --continue-on-collection-errors \
  --junitxml=/logs/verifier/junit.xml \
  > /logs/verifier/pytest.log 2>&1
python /tests/collect_results.py
python /tests/grade.py
