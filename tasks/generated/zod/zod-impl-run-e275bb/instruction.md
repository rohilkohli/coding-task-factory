In the Zod library in `/app`, the implementation of `run` in `packages/zod/src/v4/core/visit.ts` has been removed. Its body is now a stub that fails with "not implemented". Re-implement it so it behaves the way the rest of the codebase and its documentation expect.

Current signature and documentation:

```ts
function run(s: AnyZod): AnyZod { ... }
```

The project's test suite exercises this code. These tests currently fail:

- `src/v4/classic/tests/deep-partial.test.ts > deepPartial 3-level deep nesting`
- `src/v4/classic/tests/deep-partial.test.ts > deepPartial ZodCodec: both sides recursed; preserved as ZodCodec (not degraded to ZodPipe)`
- `src/v4/classic/tests/deep-partial.test.ts > deepPartial ZodPreprocess: inner is recursed; preserved as ZodPreprocess (not degraded to ZodPipe)`
- `src/v4/classic/tests/deep-partial.test.ts > deepPartial ZodPromise: inner is recursed`
- `src/v4/classic/tests/deep-partial.test.ts > deepPartial ZodSuccess: inner is recursed`
- ... and 52 more

Make them pass without modifying any tests, and keep the rest of the test suite passing.

Run the test suite from `/app` with `npx vitest run --project zod`.
