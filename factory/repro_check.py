"""Check that generation is reproducible: the same repo/strategy/seed must
produce byte-identical task directories.

Runs generate.py twice into separate output directories and compares a hash of
every file. Test results are cached by content, so the second run re-uses the
first run's verifier results; this check covers candidate selection, mutation,
packaging and archive creation. (Test-run determinism is covered separately by
the two reference runs that detect flaky tests.)

Usage: python factory/repro_check.py --repo click --strategy bug-injection --count 3 --seed 1
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def tree_hashes(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file() and not p.name.startswith("report-")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--strategy", required=True)
    ap.add_argument("--count", type=int, default=3)
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()
    outs = []
    with tempfile.TemporaryDirectory() as tmp:
        for i in (1, 2):
            out = Path(tmp) / f"run{i}"
            subprocess.run([sys.executable, str(ROOT / "factory" / "generate.py"), "--repo", args.repo,
                            "--strategy", args.strategy, "--count", str(args.count), "--seed", str(args.seed),
                            "--out", str(out)], check=False, capture_output=True)
            outs.append(tree_hashes(out))
    same = outs[0] == outs[1] and bool(outs[0])
    tasks = sorted({k.split("/")[1] for k in outs[0] if k.count("/") >= 2})
    print(f"[{'OK' if same else 'FAIL'}] {len(outs[0])} files across {len(tasks)} tasks; identical: {same}")
    if not same:
        for k in sorted(set(outs[0]) | set(outs[1])):
            if outs[0].get(k) != outs[1].get(k):
                print("   differs:", k)
    return 0 if same else 1


if __name__ == "__main__":
    sys.exit(main())
