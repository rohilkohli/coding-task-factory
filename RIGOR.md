# Rigor certificate

Every task in this repository was checked against the criteria below. Each check is computed by `factory/certify.py` from evidence on disk: Harbor runs, calibration and adversarial reports, generation reports, task files and recorded reproducibility checks. Checks are grouped by the three pillars proposed for trustworthy code benchmarks: rigor, reliability and reproducibility (see `docs/innovation-research.md`). A check with no evidence shows as *unknown*, never as passed.

**Tasks certified: 29** (3 hand-made, 26 generated)

## Rigor (construction)

| Check | Pass | Fail | Unknown | N/A |
|---|---|---|---|---|
| Reference solution scores 1 in Harbor (oracle agent) | 29 | 0 | 0 | 0 |
| Untouched task scores 0 in Harbor (no-op agent) | 29 | 0 | 0 | 0 |
| Changed code is asserted by at least one fail-to-pass test | 29 | 0 | 0 | 0 |
| At least 75% of plausible wrong solutions are rejected | 29 | 0 | 0 | 0 |
| Every partial fix is rejected (multi-bug) | 7 | 0 | 0 | 22 |
| Pass-to-pass regression suite guards the rest of the code | 26 | 0 | 0 | 3 |

## Reliability (evaluation)

| Check | Pass | Fail | Unknown | N/A |
|---|---|---|---|---|
| Reference run twice; flaky tests excluded from grading | 29 | 0 | 0 | 0 |
| Grading in a separate sandbox that only receives the agent's output | 29 | 0 | 0 | 0 |
| `harbor lint` reports no findings | 29 | 0 | 0 | 0 |

## Reproducibility (release)

| Check | Pass | Fail | Unknown | N/A |
|---|---|---|---|---|
| Base images pinned by SHA-256 digest | 29 | 0 | 0 | 0 |
| Builds offline (no package downloads in Dockerfiles) | 29 | 0 | 0 | 0 |
| Source repository and commit recorded | 29 | 0 | 0 | 0 |
| Same seed regenerates byte-identical tasks (repro_check) | 26 | 0 | 0 | 3 |

## Wrong-solution kill rate

- **Acceptance gate:** every generated task must reject at least 75% of its plausible wrong solutions. 29/29 tasks pass this gate.
- **Stricter 95% floor:** 18/29 tasks also meet the 95% floor used to audit hardware-design benchmarks. Tasks below it are still accepted; their surviving wrong solutions are listed in the generation reports.

## Contamination disclosure

"Unknown" is a valid answer.

| Leakage type | Status for this repository |
|---|---|
| Direct (test set public) | Yes, once this repository is public. Grading tests and hidden wrong solutions are in each task's `tests/` directory. |
| Derivative (built from public code) | Yes. click, zod and jsoncpp are public, so reference solutions are upstream code a model may have memorised. Generated tasks are new *states* (injected defects, removed bodies) that do not exist upstream. |
| Temporal (data before model cutoff) | Unknown. The pinned upstream commits are from Oct–Nov 2026, but which models trained on them is not known. |
| Acquired during evaluation | Possible. Agent sandboxes use `network_mode = "public"`, because Harbor's local Docker provider cannot enforce allowlists, so an agent could download upstream code. Run on a provider that enforces `allowlist` to close this. |

## Per-task results

| Task | Set | Kind | Kill rate | All applicable checks pass |
|---|---|---|---|---|
| `click-datetime-type` | hand-made | feature-removal | 1.0 | yes |
| `jsoncpp-special-floats` | hand-made | feature-removal | 1.0 | yes |
| `zod-iban-format` | hand-made | feature-removal | 1.0 | yes |
| `click-bug-make-default-short-help-751aba` | generated/click | bug-injection | 0.833 | yes |
| `click-bug-progressbar-make-step-136663` | generated/click | bug-injection | 0.833 | yes |
| `click-bug-usageerror-show-eecb2f` | generated/click | bug-injection | 1.0 | yes |
| `click-impl-command-get-short-help-str-c209c9` | generated/click | function-removal | 1.0 | yes |
| `click-impl-group-group-277cba` | generated/click | function-removal | 0.833 | yes |
| `click-impl-zshcomplete-get-completion-args-c2d85a` | generated/click | function-removal | 0.75 | yes |
| `click-multi-format-pos-resolve-incomplete-02fc06` | generated/click | multi-bug | 0.75 | yes |
| `click-multi-init-eta-format-message-dc9e6a` | generated/click | multi-bug | 1.0 | yes |
| `click-multi-wrap-chunks-normalize-choice-da1e60` | generated/click | multi-bug | 1.0 | yes |
| `click-test-parameter-get-default-a03ebe` | generated/click | test-writing | 1.0 | yes |
| `click-test-pipepager-547cd1` | generated/click | test-writing | 1.0 | yes |
| `click-test-textwrapper-wrap-chunks-599ced` | generated/click | test-writing | 1.0 | yes |
| `jsoncpp-bug-fastwriter-writevalue-be51db` | generated/jsoncpp | bug-injection | 1.0 | yes |
| `jsoncpp-bug-ourreader-getlocationlineandcolumn-e0d025` | generated/jsoncpp | bug-injection | 1.0 | yes |
| `jsoncpp-bug-value-czstring-operator-95f29e` | generated/jsoncpp | bug-injection | 0.833 | yes |
| `jsoncpp-impl-builtstyledstreamwriter-writewithindent-46b8db` | generated/jsoncpp | function-removal | 1.0 | yes |
| `jsoncpp-impl-ourreader-readcppstylecomment-fcbe5f` | generated/jsoncpp | function-removal | 0.833 | yes |
| `jsoncpp-impl-path-resolve-087a97` | generated/jsoncpp | function-removal | 1.0 | yes |
| `jsoncpp-multi-unindent-isconvertibleto-readarray-bd1d50` | generated/jsoncpp | multi-bug | 1.0 | yes |
| `jsoncpp-multi-writearrayvalue-readnumber-bfed51` | generated/jsoncpp | multi-bug | 0.875 | yes |
| `jsoncpp-multi-writeindent-decodenumber-dfc945` | generated/jsoncpp | multi-bug | 0.875 | yes |
| `zod-bug-foldobjects-ed4597` | generated/zod | bug-injection | 0.75 | yes |
| `zod-bug-helperfn-be74f3` | generated/zod | bug-injection | 1.0 | yes |
| `zod-impl-ownpaths-c21831` | generated/zod | function-removal | 1.0 | yes |
| `zod-impl-run-e275bb` | generated/zod | function-removal | 1.0 | yes |
| `zod-multi-makeuri-replay-4cae34` | generated/zod | multi-bug | 0.833 | yes |
