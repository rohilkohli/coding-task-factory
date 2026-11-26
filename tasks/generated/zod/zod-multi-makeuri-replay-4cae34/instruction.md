Several regressions (2) have been introduced into the Zod library in `/app` (library source under `/app/packages/zod/src/v4/classic`, `/app/packages/zod/src/v4/core`, `/app/packages/zod/src/v4/mini`). They are independent defects in different parts of the library. These tests currently fail:

- `src/v4/classic/tests/apply.test.ts > basic apply (object)`
- `src/v4/classic/tests/credit-card.test.ts > z.creditCard carries the shape regex as its JSON Schema pattern`
- `src/v4/classic/tests/cyclic-data.test.ts > a .catch() that takes a shared node's issues leaves them for the other reference`
- `src/v4/classic/tests/cyclic-data.test.ts > a concurrent reference reports issues and runs checks and transforms as a sync parse does`
- `src/v4/classic/tests/cyclic-data.test.ts > a cycle that closes after an await is a back-edge, not a wait`
- ... and 185 more

Find and fix every defect in the library source. Fixing only some of them is not enough: all of the tests above must pass. Do not modify the tests; grading uses the original test suite, and every test that passed before the regressions must still pass.

Run the test suite from `/app` with `npx vitest run --project zod`.
