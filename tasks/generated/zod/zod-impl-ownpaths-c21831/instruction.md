In the Zod library in `/app`, the implementation of `ownPaths` in `packages/zod/src/v4/core/util.ts` has been removed. Its body is now a stub that fails with "not implemented". Re-implement it so it behaves the way the rest of the codebase and its documentation expect.

Current signature and documentation:

```ts
/** Gives each issue from `start` on its own path, since receivers prefix a path in place. */
export function ownPaths(issues: errors.$ZodRawIssue[], start: number): void { ... }
```

The project's test suite exercises this code. These tests currently fail:

- `src/v4/classic/tests/codec-examples.test.ts > codec transform error handling`
- `src/v4/classic/tests/preprocess.test.ts > async preprocess ctx.addIssue with parseAsync`
- `src/v4/classic/tests/preprocess.test.ts > ctx.addIssue accepts string`
- `src/v4/classic/tests/preprocess.test.ts > preprocess ctx.addIssue fatal by default`
- `src/v4/classic/tests/preprocess.test.ts > preprocess ctx.addIssue fatal true`
- ... and 16 more

Make them pass without modifying any tests, and keep the rest of the test suite passing.

Run the test suite from `/app` with `npx vitest run --project zod`.
