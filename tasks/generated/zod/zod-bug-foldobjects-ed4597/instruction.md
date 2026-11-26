A regression has been introduced into the Zod library in `/app` (library source under `/app/packages/zod/src/v4/classic`, `/app/packages/zod/src/v4/core`, `/app/packages/zod/src/v4/mini`). Some behaviour no longer matches what the project's own test suite expects. These tests currently fail:

- `src/v4/classic/tests/to-json-schema.test.ts > intersection folding a catchall constrains the sibling's keys too`
- `src/v4/classic/tests/to-json-schema.test.ts > intersection folding the emitted openness agrees with the parser for every pair of object modes`
- `src/v4/classic/tests/to-json-schema.test.ts > intersection folding two catchalls both constrain the keys neither declares`

Find the defect in the library source and fix it. Do not modify the tests: grading uses the original test suite, and every test that passed before the regression must still pass.

Run the test suite from `/app` with `npx vitest run --project zod`.
