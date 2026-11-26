# Generated tasks

## Funnel

| Repo | Strategy | Seed | Candidates tried | Accepted | Rejections | Time |
|---|---|---|---|---|---|---|
| click | bug-injection | 1 | 11 | 3 | 3 undetected, 1 hangs, 1 no-adversarial-sites, 1 weak-tests | 0.0 min (cached re-run) |
| click | function-removal | 1 | 21 | 3 | 6 no-adversarial-sites, 6 weak-tests, 4 hangs, 1 too-broad | 5.6 min |
| jsoncpp | bug-injection | 1 | 12 | 3 | 3 undetected, 2 build-failure, 2 no-adversarial-sites, 1 weak-tests | 4.9 min |
| jsoncpp | function-removal | 1 | 8 | 3 | 2 weak-tests, 1 no-adversarial-sites | 5.3 min |
| zod | bug-injection | 1 | 6 | 2 | 3 undetected | 12.9 min |
| zod | function-removal | 1 | 15 | 2 | 7 no-adversarial-sites, 5 weak-tests, 1 too-broad | 22.3 min |

**Total: 16 tasks accepted from 73 candidates.** Rejection reasons:
- 9 × undetected: no test notices the change
- 2 × too-broad: change breaks too much of the suite
- 2 × build-failure: code no longer builds/loads
- 5 × hangs: run exceeded the time limit (hang or extreme slowdown)
- 15 × weak-tests: tests accept too many wrong fixes
- 17 × no-adversarial-sites: no way to construct wrong fixes

## Accepted tasks

| Task | Language | Kind | Function | Change | F2P | P2P | Wrong fixes rejected | Difficulty |
|---|---|---|---|---|---|---|---|---|
| `click-bug-argument-process-ed152e` | python | bug-injection | `_Argument.process` | `0` -> `1` | 8 | 2595 | 6/6 | medium |
| `click-bug-make-default-short-help-751aba` | python | bug-injection | `_make_default_short_help` | `and` -> `or` | 31 | 2572 | 6/6 | easy |
| `click-bug-usageerror-show-eecb2f` | python | bug-injection | `UsageError.show` | `is not` -> `is` | 37 | 2566 | 4/4 | easy |
| `click-impl-build-prompt-c47ac0` | python | function-removal | `_build_prompt` | body removed (10 lines) | 117 | 2486 | 4/4 | medium |
| `click-impl-nosuchoption-format-message-b25755` | python | function-removal | `NoSuchOption.format_message` | body removed (3 lines) | 5 | 2598 | 1/1 | easy |
| `click-impl-optionparser-match-long-opt-c4815f` | python | function-removal | `_OptionParser._match_long_opt` | body removed (14 lines) | 458 | 2145 | 4/4 | medium |
| `jsoncpp-bug-fastwriter-writevalue-be51db` | cpp | bug-injection | `FastWriter::writeValue` | `!=` -> `==` | 5 | 335 | 6/6 | medium |
| `jsoncpp-bug-ourreader-decodestring-06c621` | cpp | bug-injection | `OurReader::decodeString` | `false` -> `true` | 5 | 335 | 4/4 | medium |
| `jsoncpp-bug-value-czstring-operator-95f29e` | cpp | bug-injection | `Value::CZString::operator==` | removed `!` | 52 | 288 | 5/6 | easy |
| `jsoncpp-impl-builtstyledstreamwriter-writewithindent-46b8db` | cpp | function-removal | `BuiltStyledStreamWriter::writeWithIndent` | body removed (4 lines) | 28 | 312 | 2/2 | easy |
| `jsoncpp-impl-path-resolve-087a97` | cpp | function-removal | `Path::resolve` | body removed (15 lines) | 1 | 339 | 6/6 | medium |
| `jsoncpp-impl-styledstreamwriter-ismultilinearray-fef4cc` | cpp | function-removal | `StyledStreamWriter::isMultilineArray` | body removed (24 lines) | 14 | 326 | 5/6 | medium |
| `zod-bug-foldobjects-ed4597` | typescript | bug-injection | `foldObjects` | `===` -> `!==` | 3 | 5542 | 3/4 | medium |
| `zod-bug-helperfn-be74f3` | typescript | bug-injection | `helperFn` | `0` -> `1` | 5 | 5540 | 1/1 | medium |
| `zod-impl-ownpaths-c21831` | typescript | function-removal | `ownPaths` | body removed (4 lines) | 21 | 5524 | 2/2 | easy |
| `zod-impl-run-e275bb` | typescript | function-removal | `run` | body removed (13 lines) | 57 | 5488 | 3/3 | medium |

## Diversity

- Languages: {'python': 6, 'cpp': 6, 'typescript': 4}
- Task kinds: {'bug-injection': 8, 'function-removal': 8}
- Difficulty (heuristic): {'medium': 10, 'easy': 6}
- Distinct source files: 11; distinct functions: 16

## Harbor verification

16/16 generated tasks pass Harbor's oracle (=1) and no-op (=0) runs.
