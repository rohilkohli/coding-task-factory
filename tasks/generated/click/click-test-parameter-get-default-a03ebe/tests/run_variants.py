"""Run a regression-test file against several implementations and grade it.

Implementations ("variants") live in --variants, one directory each, holding
only the files that differ from the pristine repository in /app:
  reference/   (empty) the correct implementation
  buggy/       the implementation with the injected defect
  wrong_*/     plausible-but-wrong implementations (hidden from the agent)

For each variant, /app is copied to a scratch directory, the variant's files
are overlaid, the test file is copied to tests/test_regression.py (so the
project's tests/conftest.py fixtures apply) and pytest is run on that file.

A test file earns reward 1 only if it
  * passes on the reference implementation        (valid),
  * fails on the defective implementation         (detects the defect), and
  * fails on at least min_rigor of the wrong ones (rigorous, not "lax").
Asserting the source text instead of behaviour fails the rigor requirement,
because most wrong implementations keep the original text around the defect.

Usage:
  run_variants.py --test FILE --variants DIR --config rigor.json --out DIR
  run_variants.py --tests-dir DIR ...   (grade several candidate files; screening)
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

APP = Path("/app")


def run_one(test_file: Path, variant: Path, timeout: int = 120) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "app"
        shutil.copytree(APP, work, symlinks=True, ignore=shutil.ignore_patterns("regression", ".git"))
        for f in variant.rglob("*"):
            if f.is_file() and f.name != ".keep":
                target = work / f.relative_to(variant)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, target)
        shutil.copy2(test_file, work / "tests" / "test_regression.py")
        env = {**os.environ, "PYTHONPATH": str(work / "src"), "PYTHONDONTWRITEBYTECODE": "1"}
        try:
            proc = subprocess.run(
                ["python", "-m", "pytest", "-p", "no:cacheprovider", "-q", "-x",
                 "-c", str(work / "pyproject.toml"), "--rootdir", str(work), str(work / "tests" / "test_regression.py")],
                cwd=work, env=env, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return "timeout"
    return {0: "passed", 5: "no-tests"}.get(proc.returncode, "failed")


def grade(test_file: Path, variants: Path, min_rigor: float) -> tuple[dict, dict]:
    names = sorted(p.name for p in variants.iterdir() if p.is_dir())
    if not test_file.exists():
        return {}, {"reward": 0, "valid": 0, "detects_bug": 0, "rigor": 0.0,
                    "wrong_implementations": sum(n.startswith("wrong_") for n in names), "wrong_rejected": 0}
    status = {name: run_one(test_file, variants / name) for name in names}
    wrong = [n for n in names if n.startswith("wrong_")]
    rejected = sum(status[n] != "passed" for n in wrong)
    valid = status.get("reference") == "passed"
    detects = status.get("buggy") in ("failed", "timeout")
    rigor = rejected / len(wrong) if wrong else 0.0
    reward = int(valid and detects and rigor >= min_rigor)
    return status, {"reward": reward, "valid": int(valid), "detects_bug": int(detects), "rigor": round(rigor, 4),
                    "wrong_implementations": len(wrong), "wrong_rejected": rejected}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", type=Path)
    ap.add_argument("--tests-dir", type=Path)
    ap.add_argument("--variants", type=Path, required=True)
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    min_rigor = json.loads(args.config.read_text())["min_rigor"]
    args.out.mkdir(parents=True, exist_ok=True)
    if args.tests_dir:  # screening: grade several candidate test files
        out = {}
        for f in sorted(args.tests_dir.glob("*.py")):
            status, scores = grade(f, args.variants, min_rigor)
            out[f.stem] = {"status": status, **scores}
        (args.out / "screening.json").write_text(json.dumps(out, indent=1))
        return
    status, scores = grade(args.test, args.variants, min_rigor)
    (args.out / "results.json").write_text(json.dumps(status, indent=1))
    (args.out / "reward.json").write_text(json.dumps(scores))
    print(json.dumps(scores))


if __name__ == "__main__":
    main()
