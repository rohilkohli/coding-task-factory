#!/bin/bash
# Reference solution: the pristine upstream file(s)
# (https://github.com/colinhacks/zod @ d40c329910436e528d3c26cb1b9179e05abebf05).
set -euo pipefail
cp /solution/files/packages/zod/src/v4/core/memoizer.ts /app/packages/zod/src/v4/core/memoizer.ts
cp /solution/files/packages/zod/src/v4/core/to-json-schema.ts /app/packages/zod/src/v4/core/to-json-schema.ts
