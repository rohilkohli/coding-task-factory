"""Record a task's fail-to-pass (F2P) and pass-to-pass (P2P) test lists.

Runs the task's verifier against
  * the reference solution, twice (to detect flaky tests), and
  * the untouched task (feature removed),
then writes
  tests/f2p.txt  tests that pass with the reference but not on the untouched task
  tests/p2p.txt  tests that pass on both
Tests whose outcome differs between the two reference runs are flaky and are
excluded from both lists. The verifier image is rebuilt with the new lists.

Usage: python factory/calibrate.py tasks/<task-name>
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, build_verifier, extract_tree, run_verifier  # noqa: E402


def passed(results: dict) -> set[str]:
    return {test for test, status in results.items() if status == "passed"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("task", type=Path)
    task = ap.parse_args().task.resolve()

    print(f"[..] building verifier image for {task.name}")
    image = build_verifier(task)

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        ref = extract_tree(task, tmp / "ref", with_solution=True)
        base = extract_tree(task, tmp / "base", with_solution=False)

        runs = {}
        for name, tree in [("reference-1", ref), ("reference-2", ref), ("untouched", base)]:
            result = run_verifier(image, task, tree, tmp / f"logs-{name}")
            runs[name] = result["_results"]
            print(f"[..] {name:<12} {len(runs[name])} tests reported, {len(passed(runs[name]))} passed")

    if not runs["reference-1"]:
        print("[FAIL] verifier produced no results for the reference solution")
        return 1

    ref1, ref2, untouched = (passed(runs[k]) for k in ("reference-1", "reference-2", "untouched"))
    flaky = ref1 ^ ref2
    stable_ref = ref1 & ref2
    f2p = sorted(stable_ref - untouched)
    p2p = sorted(stable_ref & untouched)

    (task / "tests/f2p.txt").write_text("\n".join(f2p) + "\n")
    (task / "tests/p2p.txt").write_text("\n".join(p2p) + "\n")
    summary = {"task": task.name, "f2p": len(f2p), "p2p": len(p2p), "flaky_excluded": sorted(flaky),
               "reference_not_passing": len(runs["reference-1"]) - len(ref1)}
    out = ROOT / "validation" / task.name
    out.mkdir(parents=True, exist_ok=True)
    (out / "calibration.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(f"[OK] f2p={len(f2p)} p2p={len(p2p)} flaky={len(flaky)}")

    # Bake the lists into the verifier image, then check the lists end to end:
    # the reference must now score 1 and the untouched task 0.
    image = build_verifier(task)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        ref = extract_tree(task, tmp / "ref", with_solution=True)
        base = extract_tree(task, tmp / "base", with_solution=False)
        ref_reward = run_verifier(image, task, ref, tmp / "check-ref").get("reward")
        base_reward = run_verifier(image, task, base, tmp / "check-base").get("reward")
    ok = ref_reward == 1 and base_reward == 0
    summary.update({"check_reference_reward": ref_reward, "check_untouched_reward": base_reward})
    (out / "calibration.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(f"[{'OK' if ok else 'FAIL'}] self-check: reference reward={ref_reward}, untouched reward={base_reward}")
    return 0 if ok and f2p and p2p else 1


if __name__ == "__main__":
    sys.exit(main())
