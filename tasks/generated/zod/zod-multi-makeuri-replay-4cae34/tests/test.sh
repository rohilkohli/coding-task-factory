#!/bin/bash
# Grades the agent's packages/zod/src. Writes /logs/verifier/results.json
# (test id -> status) and /logs/verifier/reward.json via grade.mjs.
set -u
mkdir -p /logs/verifier
SRC=/app/packages/zod/src

# Replace whatever tests the agent's tree contains with the pristine upstream
# tests, so edits to tests cannot affect grading.
if [ -d "$SRC" ]; then
  find "$SRC" -type d -name tests -prune -exec rm -rf {} +
  find "$SRC" -name "*.test.ts" -delete
  cp -r /opt/pristine-tests/. "$SRC/"
fi

cd /app
node node_modules/vitest/vitest.mjs run --project zod \
  --reporter=json --outputFile=/logs/verifier/vitest.json \
  > /logs/verifier/vitest.log 2>&1

node /tests/grade.mjs

# Per-defect partial credit (multi-bug tasks)
node /tests/partial_credit.mjs
