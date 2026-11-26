# Generated tasks

## Funnel

| Repo | Strategy | Seed | Candidates tried | Accepted | Rejections | Time |
|---|---|---|---|---|---|---|
| click | bug-injection | 1 | 4 | 3 | 1 undetected | 0.0 min (cached re-run) |
| click | function-removal | 1 | 14 | 3 | 4 weak-tests, 3 hangs, 2 too-few-wrong-fixes, 1 too-broad | 0.0 min (cached re-run) |
| click | multi-bug (2 bugs) | 1 | 3 | 2 | no rejected groups; single-bug pool: 6 validated from 13 (5 undetected, 1 too-few-wrong-fixes, 1 weak-tests) | 0.0 min (cached re-run) |
| click | multi-bug (3 bugs) | 1 | 2 | 1 | no rejected groups; single-bug pool: 6 validated from 12 (2 undetected, 1 hangs, 1 too-few-wrong-fixes, 1 weak-tests) | 13.0 min |
| jsoncpp | bug-injection | 1 | 13 | 3 | 3 too-few-wrong-fixes, 3 undetected, 2 build-failure, 2 weak-tests | 0.6 min |
| jsoncpp | function-removal | 1 | 9 | 3 | 4 weak-tests, 1 too-few-wrong-fixes | 0.0 min (cached re-run) |
| jsoncpp | multi-bug (2 bugs) | 1 | 3 | 2 | no rejected groups; single-bug pool: 6 validated from 33 (8 undetected, 7 too-few-wrong-fixes, 6 weak-tests, 2 build-failure, 2 too-broad, 1 hangs) | 9.7 min |
| jsoncpp | multi-bug (3 bugs) | 1 | 2 | 1 | no rejected groups; single-bug pool: 6 validated from 42 (11 too-few-wrong-fixes, 10 weak-tests, 7 undetected, 4 too-broad, 2 build-failure) | 9.5 min |
| zod | bug-injection | 1 | 6 | 2 | 3 undetected | 6.8 min |
| zod | function-removal | 1 | 15 | 2 | 7 too-few-wrong-fixes, 5 weak-tests, 1 too-broad | 13.6 min |
| zod | multi-bug (2 bugs) | 1 | 2 | 1 | no rejected groups; single-bug pool: 4 validated from 13 (5 undetected, 3 too-few-wrong-fixes) | 30.5 min |

**Total: 23 tasks accepted from 186 candidates.** Rejection reasons:
- 34 × undetected: no test notices the change
- 8 × too-broad: change breaks too much of the suite
- 6 × build-failure: code no longer builds/loads
- 5 × hangs: run exceeded the time limit (hang or extreme slowdown)
- 33 × weak-tests: tests accept too many wrong fixes
- 36 × too-few-wrong-fixes: fewer than 3 wrong fixes could be built

## Accepted tasks

| Task | Language | Kind | Function(s) | Change | Locations | F2P | P2P | Wrong fixes rejected | Difficulty (score) |
|---|---|---|---|---|---|---|---|---|---|
| `click-bug-make-default-short-help-751aba` | python | bug-injection | `_make_default_short_help` | `and` -> `or` | 1 | 31 | 2572 | 5/6 | easy (-1) |
| `click-bug-progressbar-make-step-136663` | python | bug-injection | `ProgressBar.make_step` | `and` -> `or` | 1 | 2 | 2601 | 5/6 | medium (1) |
| `click-bug-usageerror-show-eecb2f` | python | bug-injection | `UsageError.show` | `is not` -> `is` | 1 | 37 | 2566 | 6/6 | easy (-1) |
| `click-impl-command-get-short-help-str-c209c9` | python | function-removal | `Command.get_short_help_str` | body removed (9 lines) | 1 | 30 | 2573 | 3/3 | medium (1) |
| `click-impl-group-group-277cba` | python | function-removal | `Group.group` | body removed (20 lines) | 1 | 7 | 2596 | 5/6 | medium (2) |
| `click-impl-zshcomplete-get-completion-args-c2d85a` | python | function-removal | `ZshComplete.get_completion_args` | body removed (8 lines) | 1 | 5 | 2598 | 3/4 | medium (1) |
| `click-multi-format-pos-resolve-incomplete-02fc06` | python | multi-bug | `ProgressBar.format_pos, _resolve_incomplete` | ProgressBar.format_pos: `is not` -> `is`; _resolve_incomplete: `and` -> `or` | 2 | 33 | 2570 | 6/8 (incl. 2 partial) | hard (3) |
| `click-multi-init-eta-format-message-dc9e6a` | python | multi-bug | `HelpFormatter.__init__, ProgressBar.eta, MissingParameter.format_message` | HelpFormatter.__init__: `0` -> `1`; ProgressBar.eta: `-` -> `+`; MissingParameter.format_message: `is not` -> `is` | 3 | 46 | 2557 | 12/12 (incl. 6 partial) | hard (5) |
| `click-multi-wrap-chunks-normalize-choice-da1e60` | python | multi-bug | `TextWrapper._wrap_chunks, Choice.normalize_choice` | TextWrapper._wrap_chunks: `+` -> `-`; Choice.normalize_choice: `and` -> `or` | 2 | 290 | 2313 | 8/8 (incl. 2 partial) | hard (3) |
| `jsoncpp-bug-fastwriter-writevalue-be51db` | cpp | bug-injection | `FastWriter::writeValue` | `!=` -> `==` | 1 | 5 | 335 | 6/6 | easy (0) |
| `jsoncpp-bug-ourreader-getlocationlineandcolumn-e0d025` | cpp | bug-injection | `OurReader::getLocationLineAndColumn` | `==` -> `!=` | 1 | 1 | 339 | 6/6 | medium (1) |
| `jsoncpp-bug-value-czstring-operator-95f29e` | cpp | bug-injection | `Value::CZString::operator==` | removed `!` | 1 | 52 | 288 | 5/6 | easy (-1) |
| `jsoncpp-impl-builtstyledstreamwriter-writewithindent-46b8db` | cpp | function-removal | `BuiltStyledStreamWriter::writeWithIndent` | body removed (4 lines) | 1 | 28 | 312 | 3/3 | medium (1) |
| `jsoncpp-impl-ourreader-readcppstylecomment-fcbe5f` | cpp | function-removal | `OurReader::readCppStyleComment` | body removed (11 lines) | 1 | 69 | 271 | 5/6 | medium (1) |
| `jsoncpp-impl-path-resolve-087a97` | cpp | function-removal | `Path::resolve` | body removed (15 lines) | 1 | 1 | 339 | 6/6 | hard (3) |
| `jsoncpp-multi-unindent-isconvertibleto-readarray-bd1d50` | cpp | multi-bug | `StyledStreamWriter::unindent, Value::isConvertibleTo, Reader::readArray` | StyledStreamWriter::unindent: `>=` -> `<=`; Value::isConvertibleTo: `&&` -> `\|\|`; Reader::readArray: `true` -> `false` | 3 | 44 | 296 | 12/12 (incl. 6 partial) | hard (5) |
| `jsoncpp-multi-writearrayvalue-readnumber-bfed51` | cpp | multi-bug | `StyledStreamWriter::writeArrayValue, Reader::readNumber` | StyledStreamWriter::writeArrayValue: `==` -> `!=`; Reader::readNumber: `==` -> `!=` | 2 | 78 | 262 | 7/8 (incl. 2 partial) | hard (3) |
| `jsoncpp-multi-writeindent-decodenumber-dfc945` | cpp | multi-bug | `StyledWriter::writeIndent, Reader::decodeNumber` | StyledWriter::writeIndent: `1` -> `2`; Reader::decodeNumber: `0` -> `1` | 2 | 85 | 255 | 7/8 (incl. 2 partial) | hard (3) |
| `zod-bug-foldobjects-ed4597` | typescript | bug-injection | `foldObjects` | `===` -> `!==` | 1 | 3 | 5542 | 3/4 | easy (0) |
| `zod-bug-helperfn-be74f3` | typescript | bug-injection | `helperFn` | `0` -> `1` | 1 | 5 | 5540 | 3/3 | easy (0) |
| `zod-impl-ownpaths-c21831` | typescript | function-removal | `ownPaths` | body removed (4 lines) | 1 | 21 | 5524 | 4/4 | medium (1) |
| `zod-impl-run-e275bb` | typescript | function-removal | `run` | body removed (13 lines) | 1 | 57 | 5488 | 4/4 | medium (1) |
| `zod-multi-makeuri-replay-4cae34` | typescript | multi-bug | `makeURI, replay` | makeURI: `===` -> `!==`; replay: `1` -> `0` | 2 | 190 | 5355 | 5/6 (incl. 2 partial) | hard (3) |

## Diversity

- Languages: {'python': 9, 'cpp': 9, 'typescript': 5}
- Task kinds: {'bug-injection': 8, 'function-removal': 8, 'multi-bug': 7}
- Difficulty (static score: locations, files, lines, failure signal): {'easy': 6, 'medium': 9, 'hard': 8}
- Distinct source files: 16; distinct functions: 32

## Harbor verification

23/23 generated tasks pass Harbor's oracle (=1) and no-op (=0) runs.
