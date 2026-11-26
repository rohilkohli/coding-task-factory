"""Adversarial check: every plausible-but-wrong solution must score 0.

For a factory task this script:
  1. builds the task's verifier image (tests/Dockerfile),
  2. reconstructs the reference solution tree (app-base + solution/files),
  3. grades the unmodified reference as a control (must score 1),
  4. applies each mutant in validation/<task>/mutants.json to a copy of the
     reference and grades it with the task's own tests/test.sh (must score 0).

A mutant that still scores 1 is a "survivor": the hidden tests failed to catch
a wrong solution, so the task's tests need strengthening.

mutants.json entries:
  {"id": ..., "description": ...,
   "edits": [{"file": <path relative to /app>, "old": ..., "new": ..., "all": false}]}
(the single-edit shorthand {"file", "old", "new"} is also accepted)

Optional validation/<task>/meta.json: {"upstream_tests": [names]} reports how
many mutants the upstream tests alone would have caught.

Usage: python factory/adversarial.py tasks/<task-name>
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (ROOT, artifact_rel_paths, build_verifier,  # noqa: E402
                    extract_tree, run_verifier)


def apply_mutant(app: Path, task: Path, mutant: dict, dest_root: Path) -> Path:
    """Copy the reference tree's artifact dirs and apply the mutant's edits.
    Returns a tree root usable by run_verifier."""
    for rel in artifact_rel_paths(task):
        shutil.copytree(app / rel, dest_root / rel, symlinks=True)
    edits = mutant.get("edits") or [{k: mutant[k] for k in ("file", "old", "new")}]
    for edit in edits:
        target = dest_root / edit["file"]
        if not target.exists():
            raise ValueError(f"mutant {mutant['id']}: {edit['file']} is not inside an artifact path")
        text = target.read_text()
        count = text.count(edit["old"])
        if count == 0 or (count > 1 and not edit.get("all")):
            raise ValueError(f"mutant {mutant['id']}: 'old' text found {count} times in {edit['file']}")
        target.write_text(text.replace(edit["old"], edit["new"]))
    return dest_root


def failed_tests(results: dict) -> list[str]:
    return sorted(t for t, s in results.items() if s not in ("passed", "skipped", "pending", "todo"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("task", type=Path)
    task = ap.parse_args().task.resolve()

    vdir = ROOT / "validation" / task.name
    mutants = json.loads((vdir / "mutants.json").read_text())
    meta_file = vdir / "meta.json"
    upstream = json.loads(meta_file.read_text()).get("upstream_tests", []) if meta_file.exists() else []

    def caught_by_upstream(failed: list[str], regression_ok) -> bool:
        return regression_ok == 0 or any(u in t for t in failed for u in upstream)

    print(f"[..] building verifier image for {task.name}")
    image = build_verifier(task)

    results = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        app = extract_tree(task, tmp / "ref", with_solution=True)

        control = run_verifier(image, task, app, tmp / "logs-control")
        print(f"[{'OK' if control.get('reward') == 1 else 'FAIL'}] control (reference solution): "
              f"reward={control.get('reward')}")

        for m in mutants:
            src = apply_mutant(app, task, m, tmp / f"mut-{m['id']}")
            r = run_verifier(image, task, src, tmp / f"logs-{m['id']}")
            failed = failed_tests(r["_results"])
            killed = r.get("reward") == 0
            results.append({
                "id": m["id"], "description": m["description"], "reward": r.get("reward"),
                "killed": killed, "feature_pass_rate": r.get("feature_pass_rate"),
                "regression_ok": r.get("regression_ok"),
                "caught_by_upstream_tests": caught_by_upstream(failed, r.get("regression_ok")) if upstream else None,
                "failed_tests": failed,
            })
            print(f"[{'OK' if killed else 'FAIL'}] {m['id']:<30} reward={r.get('reward')} "
                  f"feature_pass_rate={r.get('feature_pass_rate')} regression_ok={r.get('regression_ok')}")

    killed = sum(r["killed"] for r in results)
    report = {
        "task": task.name,
        "control_reward": control.get("reward"),
        "mutants": len(results),
        "killed": killed,
        "kill_rate": round(killed / len(results), 4) if results else None,
        "survivors": [r["id"] for r in results if not r["killed"]],
        "upstream_tests_only_killed": sum(bool(r["caught_by_upstream_tests"]) for r in results) if upstream else None,
        "results": results,
    }
    (vdir / "adversarial_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"-> kill rate {killed}/{len(results)}; report: {(vdir / 'adversarial_report.json').relative_to(ROOT)}")
    if upstream:
        print(f"-> upstream tests alone would kill {report['upstream_tests_only_killed']}/{len(results)}")
    return 0 if control.get("reward") == 1 and not report["survivors"] else 1


if __name__ == "__main__":
    sys.exit(main())
