"""Summarise generator runs: funnel, accepted tasks and diversity.

Reads tasks/generated/<repo>/report-*.json (written by generate.py) and the
task.toml of every generated task, and prints Markdown.

Usage: python factory/report.py > tasks/generated/REPORT.md
"""

from __future__ import annotations

import json
import sys
import tomllib
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / "tasks" / "generated"

REASONS = {
    "undetected": "no test notices the change",
    "too-broad": "change breaks too much of the suite",
    "build-failure": "code no longer builds/loads",
    "hangs": "run exceeded the time limit (hang or extreme slowdown)",
    "weak-tests": "tests accept too many wrong fixes",
    "no-adversarial-sites": "no way to construct wrong fixes",
}


def main() -> None:
    reports = sorted(GEN.glob("*/report-*.json"))
    print("# Generated tasks\n")
    print("## Funnel\n")
    print("| Repo | Strategy | Seed | Candidates tried | Accepted | Rejections | Time |")
    print("|---|---|---|---|---|---|---|")
    totals = Counter()
    for path in reports:
        r = json.loads(path.read_text())
        rej = Counter()
        for key, n in r["funnel"].items():
            if key.startswith("rejected:"):
                rej[key.split(":", 1)[1]] += n
                totals[key.split(":", 1)[1]] += n
        totals["tried"] += r["candidates_tried"]
        totals["accepted"] += r["accepted"]
        rej_s = ", ".join(f"{n} {k}" for k, n in rej.most_common()) or "none"
        print(f"| {r['repo']} | {r['strategy']} | {r['seed']} | {r['candidates_tried']} | {r['accepted']} | "
              f"{rej_s} | {r['elapsed_sec'] / 60:.1f} min{' (cached re-run)' if r['elapsed_sec'] < 30 else ''} |")
    print(f"\n**Total: {totals['accepted']} tasks accepted from {totals['tried']} candidates.** Rejection reasons:")
    for key, label in REASONS.items():
        if totals[key]:
            print(f"- {totals[key]} × {key}: {label}")

    tasks = sorted(p for p in GEN.glob("*/*") if (p / "task.toml").exists())
    print("\n## Accepted tasks\n")
    print("| Task | Language | Kind | Function | Change | F2P | P2P | Wrong fixes rejected | Difficulty |")
    print("|---|---|---|---|---|---|---|---|---|")
    langs, kinds, levels, files = Counter(), Counter(), Counter(), Counter()
    for t in tasks:
        m = tomllib.loads((t / "task.toml").read_text())["metadata"]
        langs[m["language"]] += 1
        kinds[m["generator"]] += 1
        levels[m["difficulty"]] += 1
        files[m["file"]] += 1
        print(f"| `{t.name}` | {m['language']} | {m['generator']} | `{m['function']}` | {m['change']} | "
              f"{m['f2p_tests']} | {m['p2p_tests']} | {m['adversarial_killed']}/{m['adversarial_mutants']} | "
              f"{m['difficulty']} |")
    print("\n## Diversity\n")
    print(f"- Languages: {dict(langs)}")
    print(f"- Task kinds: {dict(kinds)}")
    print(f"- Difficulty (heuristic): {dict(levels)}")
    print(f"- Distinct source files: {len(files)}; distinct functions: {len(tasks)}")
    check_files = sorted(GEN.glob("*/harbor-check.json"))
    if check_files:
        ok = sum(json.loads(p.read_text())["passed"] for p in check_files)
        n = sum(json.loads(p.read_text())["tasks"] for p in check_files)
        print(f"\n## Harbor verification\n\n{ok}/{n} generated tasks pass Harbor's oracle (=1) and no-op (=0) runs.")


if __name__ == "__main__":
    sys.exit(main())
