A regression has been introduced into the Zod library in `/app` (library source under `/app/packages/zod/src/v4/classic`, `/app/packages/zod/src/v4/core`, `/app/packages/zod/src/v4/mini`). Some behaviour no longer matches what the project's own test suite expects. These tests currently fail:

- `src/v4/core/tests/compile-differential.test.ts > superRefine adds issues`
- `src/v4/core/tests/compile-generative.test.ts > random schemas parse identically through the interpreter and the compiler`
- `src/v4/core/tests/compile.test.ts > matches Zod: superRefine`
- `src/v4/core/tests/compile.test.ts > superRefine basic`
- `src/v4/core/tests/compile.test.ts > superRefine with multiple issues`

Find the defect in the library source and fix it. Do not modify the tests: grading uses the original test suite, and every test that passed before the regression must still pass.

Run the test suite from `/app` with `npx vitest run --project zod`.
