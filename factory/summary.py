"""Print a Markdown validation summary for every task under tasks/.

Reads validation/<task>/calibration.json, validation/<task>/adversarial_report.json
and the Harbor job results in jobs/<task-prefix>-oracle-x3 and jobs/<task-prefix>-nop.

Usage: python factory/summary.py > validation/SUMMARY.md
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, task_config  # noqa: E402


def harbor_rewards(job: str) -> list:
    rewards = []
    for result in sorted((ROOT / "jobs" / job).glob("*/result.json")):
        data = json.loads(result.read_text())
        rewards.append(((data.get("verifier_result") or {}).get("rewards") or {}).get("reward"))
    return rewards


def main() -> None:
    rows = []
    for task in sorted(p for p in (ROOT / "tasks").iterdir() if (p / "task.toml").exists()):
        meta = task_config(task).get("metadata", {})
        vdir = ROOT / "validation" / task.name
        cal = json.loads((vdir / "calibration.json").read_text())
        adv = json.loads((vdir / "adversarial_report.json").read_text())
        prefix = task.name.split("-")[0]
        oracle = harbor_rewards(f"{prefix}-oracle-x3")
        nop = harbor_rewards(f"{prefix}-nop")
        rows.append((task.name, meta.get("language", "?"), meta.get("difficulty", "?"), cal, adv, oracle, nop))

    print("# Validation summary\n")
    print("| Task | Language | Difficulty | Feature tests (F2P) | Regression tests (P2P) | Flaky | "
          "Oracle (Harbor) | No-op (Harbor) | Wrong solutions rejected | Upstream tests alone |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for name, lang, diff, cal, adv, oracle, nop in rows:
        print(f"| {name} | {lang} | {diff} | {cal['f2p']} | {cal['p2p']} | {len(cal['flaky_excluded'])} | "
              f"{', '.join(map(str, oracle)) or '-'} | {', '.join(map(str, nop)) or '-'} | "
              f"{adv['killed']}/{adv['mutants']} | {adv.get('upstream_tests_only_killed', '-')}/{adv['mutants']} |")
    total_k = sum(r[4]["killed"] for r in rows)
    total_m = sum(r[4]["mutants"] for r in rows)
    total_u = sum(r[4].get("upstream_tests_only_killed") or 0 for r in rows)
    print(f"\n**Wrong solutions rejected overall: {total_k}/{total_m}** "
          f"(upstream tests alone: {total_u}/{total_m}).\n")
    print("Feature tests count each test case as the harness reports it; zod's vitest reports "
          "runtime and type-level checks separately, and click's F2P includes the whole "
          "`tests/test_info_dict.py` module, which cannot load without `click.DateTime`.")


if __name__ == "__main__":
    main()
