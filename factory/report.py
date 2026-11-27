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
    "too-few-wrong-fixes": "fewer than 3 wrong fixes could be built",
    "masked-bugs": "a partial fix passed (one bug hides another)",
    "oracle-unavailable": "test-writing: no upstream test module to build a reference test from",
    "oracle-invalid": "test-writing: reference test does not pass/fail as required",
    "oracle-not-rigorous": "test-writing: reference test rejects too few wrong implementations",
    "cheat-test-passes": "test-writing: a cheating test (no assertion / always fails / source peek) would earn credit",
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
        strategy = r["strategy"] + (f" ({r['bugs_per_task']} bugs)" if r.get("bugs_per_task") else "")
        if r.get("single_bug_stage"):
            st = r["single_bug_stage"]
            pool_rej = Counter()
            for key, n in st["funnel"].items():
                if key.startswith("rejected:"):
                    pool_rej[key.split(":", 1)[1]] += n
                    totals[key.split(":", 1)[1]] += n
            pool_s = ", ".join(f"{n} {k}" for k, n in pool_rej.most_common()) or "no rejections"
            rej_s = (f"{rej_s if rej_s != 'none' else 'no rejected groups'}; single-bug pool: "
                     f"{st['validated_bugs']} validated from {st['candidates_tried']} ({pool_s})")
            totals["tried"] += st["candidates_tried"]
        print(f"| {r['repo']} | {strategy} | {r['seed']} | {r['candidates_tried']} | {r['accepted']} | "
              f"{rej_s} | {r['elapsed_sec'] / 60:.1f} min{' (cached re-run)' if r['elapsed_sec'] < 30 else ''} |")
    print(f"\n**Total: {totals['accepted']} tasks accepted from {totals['tried']} candidates.** Rejection reasons:")
    for key, label in REASONS.items():
        if totals[key]:
            print(f"- {totals[key]} × {key}: {label}")

    tasks = sorted(p for p in GEN.glob("*/*") if (p / "task.toml").exists())
    print("\n## Accepted tasks\n")
    print("| Task | Language | Kind | Function(s) | Change | Locations | F2P | P2P | Wrong fixes rejected | "
          "Difficulty (score) |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    langs, kinds, levels, files, functions = Counter(), Counter(), Counter(), Counter(), Counter()
    for t in tasks:
        m = tomllib.loads((t / "task.toml").read_text())["metadata"]
        langs[m["language"]] += 1
        kinds[m["generator"]] += 1
        levels[m["difficulty"]] += 1
        for f in m["file"].split(", "):
            files[f] += 1
        for fn in m["function"].split(", "):
            functions[fn] += 1
        partial = f" (incl. {m['partial_fixes_rejected']} partial)" if m.get("partial_fixes_rejected") else ""
        if m["generator"] == "test-writing":
            partial = (f" cheat tests; hidden wrong impls: {m['wrong_implementations']}, "
                       f"reference test rigor {m['oracle_rigor']}")
        change = m["change"].replace("|", "\\|")  # `||` would break the Markdown table
        print(f"| `{t.name}` | {m['language']} | {m['generator']} | `{m['function']}` | {change} | "
              f"{m.get('change_locations', 1)} | {m['f2p_tests']} | {m['p2p_tests']} | "
              f"{m['adversarial_killed']}/{m['adversarial_mutants']}{partial} | "
              f"{m['difficulty']} ({m.get('difficulty_score', '-')}) |")
    print("\n## Diversity\n")
    print(f"- Languages: {dict(langs)}")
    print(f"- Task kinds: {dict(kinds)}")
    print(f"- Difficulty (static score: locations, files, lines, failure signal): {dict(levels)}")
    print(f"- Distinct source files: {len(files)}; distinct functions: {len(functions)}")
    check_files = sorted(GEN.glob("*/harbor-check.json"))
    if check_files:
        ok = sum(json.loads(p.read_text())["passed"] for p in check_files)
        n = sum(json.loads(p.read_text())["tasks"] for p in check_files)
        print(f"\n## Harbor verification\n\n{ok}/{n} generated tasks pass Harbor's oracle (=1) and no-op (=0) runs.")


if __name__ == "__main__":
    sys.exit(main())
