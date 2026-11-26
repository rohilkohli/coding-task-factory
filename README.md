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
3. **Adversarial strength.** Up to six plausible wrong fixes are graded: the
   reference plus one other mutation in the same function, or another
   "fix" at the injected site. If more than 25% of them would score 1, the
   candidate is rejected as *weak-tests*.
4. **Package.** The candidate becomes a complete Harbor task with a
   deterministic tar archive, the reference solution, F2P/P2P lists, the
   instruction, a heuristic difficulty and full provenance in `task.toml`.

Selection is seeded and spreads candidates across files. The same seed gives
byte-identical tasks (`factory/repro_check.py`). `factory/harbor_check.py`
runs Harbor's oracle and no-op agents over a generated set, and
`factory/report.py` writes the funnel and diversity report.

### First generated batch (seed 1), see `tasks/generated/REPORT.md`

- **16 tasks accepted from 73 candidates.** Rejections: 17 had no way to
  build wrong fixes, 15 had weak tests, 9 went undetected, 5 timed out
  (hangs), 2 were too broad and 2 failed to build.
- **3 languages:** Python 6, C++ 6, TypeScript 4. **2 kinds:** 8
  bug-injection and 8 function-removal. **Coverage:** 11 source files, 16
  distinct functions.
- **All 16 pass `harbor lint`**, and Harbor's oracle (= 1) and no-op (= 0)
  runs.
- **Same seed gives byte-identical tasks.** `repro_check.py` confirmed this
  for click bug-injection, jsoncpp function-removal and zod bug-injection.

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
