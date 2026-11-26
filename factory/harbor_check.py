"""Run Harbor's oracle and no-op agents on every generated task in a directory.

For each task the oracle (reference solution) must score 1 and the no-op agent
(task left untouched) must score 0. Results are written to
<dir>/harbor-check.json.

Usage: python factory/harbor_check.py tasks/generated/click [--concurrency 3]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def rewards(job_dir: Path) -> dict[str, float | None]:
    out = {}
    for result in job_dir.glob("*/result.json"):
        data = json.loads(result.read_text())
        task = data.get("task_name") or result.parent.name.rsplit("__", 1)[0]
        out[task.split("/")[-1]] = ((data.get("verifier_result") or {}).get("rewards") or {}).get("reward")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("tasks_dir", type=Path)
    ap.add_argument("--concurrency", type=int, default=3)
    args = ap.parse_args()
    tasks = sorted(p for p in args.tasks_dir.resolve().iterdir() if (p / "task.toml").exists())
    jobs_root = ROOT / "jobs" / "generated" / args.tasks_dir.name
    summary = {}
    for agent in ("oracle", "nop"):
        job = f"{agent}"
        subprocess.run(["harbor", "run", "-p", str(args.tasks_dir.resolve()), "-a", agent, "-e", "docker",
                        "-o", str(jobs_root), "--job-name", job, "-n", str(args.concurrency), "-y"],
                       capture_output=True)
        for name, reward in rewards(jobs_root / job).items():
            summary.setdefault(name, {})[agent] = reward
    ok = {t.name: summary.get(t.name, {}).get("oracle") == 1 and summary.get(t.name, {}).get("nop") == 0
          for t in tasks}
    report = {"tasks": len(tasks), "passed": sum(ok.values()),
              "results": {t: {**summary.get(t, {}), "ok": ok[t]} for t in sorted(ok)}}
    (args.tasks_dir / "harbor-check.json").write_text(json.dumps(report, indent=2) + "\n")
    for t in sorted(ok):
        print(f"[{'OK' if ok[t] else 'FAIL'}] {t}: oracle={summary.get(t, {}).get('oracle')} "
              f"nop={summary.get(t, {}).get('nop')}")
    print(f"-> {report['passed']}/{report['tasks']} tasks pass oracle=1 / nop=0")
    return 0 if report["passed"] == report["tasks"] else 1


if __name__ == "__main__":
    sys.exit(main())
