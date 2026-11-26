"""Run jsoncpp's test suites one case at a time and record per-test results.

  unit/<Fixture/name>     upstream unit tests (src/test_lib_json), one process each
  hidden/<Fixture/name>   hidden feature tests, one process each
  data/<file> [<writer>]  upstream data-driven tests (test/runjsontests.py)

Running each unit test in its own process means a crash (e.g. an abort in the
fuzz harness) fails only that test instead of the whole suite. A missing
binary (build failure) simply produces no results, which grades as 0.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

LOGS = Path("/logs/verifier")


def run_cases(binary: Path, prefix: str, results: dict[str, str]) -> None:
    if not binary.exists():
        return
    listing = subprocess.run([str(binary), "--list-tests"], capture_output=True, text=True, timeout=60)
    for name in filter(None, (line.strip() for line in listing.stdout.splitlines())):
        try:
            proc = subprocess.run([str(binary), "--test", name], capture_output=True, timeout=60)
            results[f"{prefix}/{name}"] = "passed" if proc.returncode == 0 else "failed"
        except subprocess.TimeoutExpired:
            results[f"{prefix}/{name}"] = "failed"


def run_data_tests(runner: Path, results: dict[str, str]) -> None:
    """Upstream data-driven tests, one independent pass per writer class.

    test/runjsontests.py stops after the first writer pass that has a failure,
    so each pass is run on its own here; otherwise a failure with one writer
    would hide (and mark as failed) every result for the later writers."""
    if not runner.exists():
        return
    driver = (
        "import sys; sys.path.insert(0, '/app/test'); import runjsontests as r\n"
        "try:\n    r.runAllTests(sys.argv[1], sys.argv[2], writerClass=sys.argv[3])\n"
        "except r.FailError:\n    pass\n"
    )
    log = []
    for writer in ("StyledWriter", "StyledStreamWriter", "BuiltStyledStreamWriter"):
        try:
            proc = subprocess.run([sys.executable, "-c", driver, str(runner), "/app/test/data", writer],
                                  capture_output=True, text=True, timeout=600, cwd="/app")
            out = proc.stdout
            log.append(f"### {writer}\n{proc.stdout}\n--- stderr ---\n{proc.stderr}")
        except subprocess.TimeoutExpired:
            out = ""
        body = out.split("Failure details:", 1)[0]
        for m in re.finditer(r"TESTING: (\S+)(.*?)(?=TESTING: |\Z)", body, re.S):
            verdict = m.group(2)
            ok = re.search(r"\bOK\b", verdict) and "FAILED" not in verdict
            results[f"data/{Path(m.group(1)).name} [{writer}]"] = "passed" if ok else "failed"
    (LOGS / "data_tests.log").write_text("\n".join(log))


def main() -> None:
    build = Path(sys.argv[1])
    results: dict[str, str] = {}
    run_cases(build / "jsoncpp_test", "unit", results)
    run_cases(build / "hidden_tests", "hidden", results)
    run_data_tests(build / "jsontestrunner", results)
    (LOGS / "results.json").write_text(json.dumps(results, indent=1, sort_keys=True))
    print(f"{sum(s == 'passed' for s in results.values())}/{len(results)} test cases passed")


if __name__ == "__main__":
    main()
