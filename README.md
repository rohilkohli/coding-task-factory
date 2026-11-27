# Coding Task Factory

Creates, validates and packages realistic coding tasks from real codebases
(pallets/click, colinhacks/zod, open-source-parsers/jsoncpp) in the
[Harbor](https://www.harborframework.com/) task format, for evaluating AI
coding agents. Built for the Innodata AI Hackathon 2026, Challenge 01.

## Sample tasks

| Task | Language | What the agent must build |
|---|---|---|
| `click-datetime-type` | Python | click's `DateTime` parameter type |
| `zod-iban-format` | TypeScript | IBAN validation across zod core, classic, mini, JSON Schema and the AOT compiler |
| `jsoncpp-special-floats` | C++ | the `allowSpecialFloats` reader setting (`NaN`, `Infinity`, `-Infinity`, `+Infinity`) |

Each task is a feature-removal task. A real feature is removed from the
repository at a pinned commit, along with its tests and git history. The agent
gets a developer-style requirement, the upstream implementation is the
reference solution, and grading uses the upstream tests plus hidden tests.

## Validation (see `validation/SUMMARY.md`)

| Task | Feature tests | Regression tests | Flaky | Oracle ×3 | No-op | Wrong solutions rejected | Upstream tests alone |
|---|---|---|---|---|---|---|---|
| click-datetime-type | 58 | 2,563 | 0 | 1, 1, 1 | 0 | 14/14 | 9/14 |
| jsoncpp-special-floats | 11 | 342 | 0 | 1, 1, 1 | 0 | 14/14 | 11/14 |
| zod-iban-format | 56 | 5,519 | 0 | 1, 1, 1 | 0 | 14/14 | 9/14 |

Overall, the hidden tests reject 42/42 plausible-but-wrong solutions. The
upstream tests alone reject 29/42. On zod, the adversarial check surfaced two
real gaps (IBAN length bounds and abort semantics), and the hidden tests were
strengthened to close them.

## Automatic task generation

`factory/generate.py` produces new tasks from any of the three repositories
without human or LLM input:

| Strategy | What changes | What the agent must do |
|---|---|---|
| `bug-injection` | one realistic single-token defect inside a function (`<` → `<=`, `==` → `!=`, `&&` → `\|\|`, dropped `not`/`!`, `true` → `false`, off-by-one literal) | find and fix the regression; the failing tests are listed |
| `function-removal` | a function body replaced by a "not implemented" stub; signature and docs kept (for C++, the docs come from the public header) | re-implement the function |
| `multi-bug` | 2–3 individually validated defects in different functions, preferably different files | find and fix every defect; fixing only some still fails (partial credit reported per defect) |
| `test-writing` (Python) | a validated defect is injected and **the upstream tests that catch it are removed** | write `/app/regression/test_regression.py` that exposes the defect; graded for *rigor* (below) |

Functions and mutation sites are found with each language's own parser.
Python uses `ast`/`tokenize`, TypeScript uses the TypeScript compiler API, and
C++ uses a lexer that skips strings, comments and preprocessor lines plus brace
matching. Mutations therefore never land in strings or comments.

Every candidate passes the same gates as the hand-made tasks before it is kept:

1. **Screen.** The upstream suite runs in the task's verifier against the
   modified code. A candidate is rejected as *undetected* if no test notices
   the change, *too-broad* if more than 25% of the suite fails, *build-failure*
   if the code no longer builds, and *hangs* if it exceeds a timeout derived
   from the reference run time.
2. **Fail-to-pass / pass-to-pass.** F2P and P2P lists come from two reference
   runs, which also detect flaky tests, plus the candidate run.
3. **Adversarial strength.** Up to six plausible wrong fixes are graded on top
   of the reference: an operator mutation, a **statement deletion** (the
   pseudo-testedness operator from the mutation-testing literature, which
   works even on functions without operators), or another "fix" at the
   injected site. Deletions that would only cause a compile or name error,
   and deletions of assertions, are skipped, so the wrong fixes stay
   plausible. A task needs **at least 3 wrong fixes** (*too-few-wrong-fixes*
   otherwise). If more than 25% would score 1, it is rejected as
   *weak-tests*. For `multi-bug`, **every partial fix** (some defects left in)
   must also score 0 (*masked-bugs* otherwise).
4. **Package.** The candidate becomes a complete Harbor task with a
   deterministic tar archive, the reference solution, F2P/P2P lists, the
   instruction, a static difficulty score and full provenance in `task.toml`.

**Test-writing tasks are graded for rigor, not just fail-to-pass.** The
agent's test file runs against the correct implementation (it must pass), the
defective one (it must fail) and the task's hidden plausible-but-wrong
implementations, which it must reject at a rate of at least 75%. Research on
bug-reproduction tests shows that a test can fail on the bug and pass on the
fix while still accepting wrong patches ("lax" tests); the rigor requirement
measures exactly that. A test-writing task is kept only if:

- the reference test, built from the removed upstream tests, earns reward 1;
  and
- three cheating tests earn 0: one without assertions, one that always fails,
  and one that only checks the source text around the defect.

**Per-defect partial credit.** Multi-bug tasks keep a strict binary `reward`
and also report `defects_fixed`, `defects_total`, `partial_credit` and
`defect_<i>_fixed`. Each defect is judged by the tests it breaks on its own.
For example, on a 3-defect task, fixing only one defect gives
`partial_credit = 0.33`.

**Rigor certificate.** `factory/certify.py` writes `RIGOR.md`, which checks
every task for rigor (construction), reliability (evaluation) and
reproducibility (release) from evidence on disk. It also includes a
contamination disclosure. All 29 tasks (3 hand-made, 26 generated) currently
pass every applicable check.

**Difficulty score.** This is a static, pre-run estimate. Published studies
find that task difficulty is predicted mainly by patch fragmentation and patch
size (see `docs/improvements-research.md`). Points are given for:

- **Locations:** 2 locations give +2; 3 or more give +3.
- **Files:** more than one file gives +1.
- **Code to write:** function bodies give +1 to +3; multi-line fixes give +1.
- **Failure signal:** 2 or fewer failing tests give +1 (harder to localise);
  30 or more give −1, but only for single-location changes.

A score of 0 or less is *easy*, 1–2 is *medium* and 3 or more is *hard*. Real
agent runs will calibrate it later.

Selection is seeded and spreads candidates across files. The same seed gives
byte-identical tasks (`factory/repro_check.py`). `factory/harbor_check.py`
runs Harbor's oracle and no-op agents over a generated set, and
`factory/report.py` writes the funnel and diversity report.

### Generated batch (seed 1), see `tasks/generated/REPORT.md`

- **26 tasks accepted from 221 candidates.** This count includes the
  single-bug pools that multi-bug and test-writing tasks are built from.
  Rejections: 42 went undetected, 38 had too few wrong fixes, 35 had weak
  tests, 8 were too broad, 6 failed to build and 5 timed out. Test-writing
  added 5 more: 3 reference tests were not rigorous enough, 1 was invalid
  and 1 task could be passed by a cheating test.
- **3 languages:** Python 12, C++ 9, TypeScript 5.
- **4 kinds:** 8 bug-injection, 8 function-removal, 7 multi-bug (two of
  them have 3 defects) and 3 test-writing.
- **Coverage:** 16 source files and 34 distinct functions.
- **Difficulty (static score):** 6 easy, 11 medium and 9 hard. The first
  batch had no hard tasks.
- **Partial fixes:** every multi-bug task rejects every partial fix. That is
  2 partial fixes for 2-bug tasks and 6 for 3-bug tasks.
- **Harbor checks:** all tasks pass `harbor lint`, and Harbor's oracle (= 1)
  and no-op (= 0) runs.
- **Reproducibility:** the same seed gives byte-identical tasks.
  `repro_check.py` confirmed this for all 12 repo/strategy combinations in
  the batch (`validation/repro-checks.json`).

**Effect of the round-2 improvements**, compared with the first batch:

- **Stricter bar, similar rejection rate.** With statement-deletion wrong
  fixes, each task needs **at least 3 wrong fixes** (before, 1 was enough),
  yet the rate of rejections for lack of wrong fixes stayed about the same:
  17 of 73 (23%) before, 13 of 61 single-task candidates (21%) now.
- **Stronger evidence.** Every accepted task is now checked against 3 to 12
  wrong fixes; before, some were checked against only 1 or 2.
- **Hard tasks.** Multi-bug tasks add a hard tier that did not exist before.

Generated zod tasks are about 44 MB each because they vendor the Node
toolchain twice. They are reproducible from the generator, so the repository
only needs the generator and the small sample tasks.

```bash
python3 factory/generate.py --repo click --strategy bug-injection --count 5 --seed 1
python3 factory/generate.py --repo jsoncpp --strategy function-removal --count 5 --seed 1
python3 factory/harbor_check.py tasks/generated/click
python3 factory/report.py > tasks/generated/REPORT.md
```

## Layout

```text
tasks/<task>/                Harbor task
  instruction.md             the requirement, as a developer would write it
  task.toml                  Harbor config, provenance, artifacts the verifier receives
  environment/               agent sandbox: offline build, pinned image digest, no git history
  solution/                  reference implementation (Harbor's oracle agent runs solve.sh)
  tests/                     separate grading sandbox: pristine tests, hidden tests,
                             f2p.txt / p2p.txt, grader
  feature_removal.diff       exactly what was removed from upstream (audit trail)
validation/<task>/           calibration.json, mutants.json, adversarial_report.json
factory/
  calibrate.py               records F2P/P2P lists (reference ×2 for flakiness, untouched ×1)
                             and self-checks reference=1 / untouched=0
  adversarial.py             grades every mutant with the task's own verifier (must be 0)
  summary.py                 builds validation/SUMMARY.md
  common.py                  shared helpers and task conventions
  brotli_tar.mjs             compresses vendored archives (decompressible with plain Node)
```

## Anti-cheating design

- **Separate verifier.** Grading runs in its own container, built from
  `tests/Dockerfile`. It receives only the agent's source directories (Harbor
  `artifacts`), never the agent's tests or configuration. For zod, whose tests
  live inside `src/`, the pristine tests are restored over the agent's tree
  before grading.
- **No answer leakage.** The agent's repository has no git history, and the
  vendored archives are bind-mounted at build time, so they never reach an
  image layer.
- **Hidden tests.** They pin every requirement in the instruction. Each task
  ships about 14 mutants: plausible wrong implementations that must all score 0.

## Run it

```bash
uv tool install harbor
harbor lint tasks/<task>
harbor run -p tasks/<task> -a oracle -e docker -o jobs -k 3
harbor run -p tasks/<task> -a nop -e docker -o jobs
python3 factory/calibrate.py tasks/<task>
python3 factory/adversarial.py tasks/<task>
python3 factory/summary.py > validation/SUMMARY.md
```

Every build is offline and reproducible. Each task vendors its repository
snapshot and test toolchain, and base images are pinned by digest.
