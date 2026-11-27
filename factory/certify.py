"""Rigor certificate for every task (hand-made and generated).

Checks are grouped by the three pillars proposed for code benchmarks: rigor in
construction, reliability in evaluation and reproducibility in release (see
docs/innovation-research.md). Every check is computed from evidence on disk:
Harbor results, calibration and adversarial reports, generation reports, the
task files themselves and recorded reproducibility checks. A check with no
evidence is reported as "unknown", never as passed.

Also reports a contamination disclosure ("unknown" is a valid answer) and how
many tasks meet a stricter 95% wrong-solution kill floor in addition to the
factory's 75% acceptance gate.

Usage: python factory/certify.py   (writes RIGOR.md and validation/rigor.json)
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NETWORK_INSTALL = re.compile(r"apt-get|apk add|npm (install|ci)|pnpm |yarn |curl |wget |git clone|"
                             r"pip install(?![^\n]*--no-index)")


def harbor_lint_ok(task: Path) -> bool | None:
    proc = subprocess.run(["harbor", "lint", "--json", str(task)], capture_output=True, text=True)
    try:
        return proc.returncode == 0 and json.loads(proc.stdout or "[]") == []
    except json.JSONDecodeError:
        return None


def dockerfile_checks(task: Path) -> tuple[bool, bool]:
    pinned, offline = True, True
    for df in (task / "environment" / "Dockerfile", task / "tests" / "Dockerfile"):
        text = df.read_text()
        for line in text.splitlines():
            if line.startswith("FROM ") and "@sha256:" not in line:
                pinned = False
        if NETWORK_INSTALL.search(text):
            offline = False
    return pinned, offline


def harbor_results(job_dirs: list[Path]) -> dict[str, list]:
    out: dict[str, list] = {}
    for job in job_dirs:
        for result in sorted(job.glob("*/result.json")):
            data = json.loads(result.read_text())
            name = (data.get("task_name") or result.parent.name.rsplit("__", 1)[0]).split("/")[-1]
            out.setdefault(name, []).append(((data.get("verifier_result") or {}).get("rewards") or {}).get("reward"))
    return out


def collect() -> list[dict]:
    rows = []
    repro = json.loads((ROOT / "validation" / "repro-checks.json").read_text()) \
        if (ROOT / "validation" / "repro-checks.json").exists() else {}

    # hand-made tasks
    oracle = harbor_results(sorted((ROOT / "jobs").glob("*-oracle-x3")))
    nop = harbor_results(sorted((ROOT / "jobs").glob("*-nop")))
    for task in sorted(p for p in (ROOT / "tasks").iterdir() if (p / "task.toml").exists()):
        cfg = tomllib.loads((task / "task.toml").read_text())
        vdir = ROOT / "validation" / task.name
        cal = json.loads((vdir / "calibration.json").read_text()) if (vdir / "calibration.json").exists() else {}
        adv = json.loads((vdir / "adversarial_report.json").read_text()) \
            if (vdir / "adversarial_report.json").exists() else {}
        rows.append({
            "task": task.name, "set": "hand-made", "kind": cfg["metadata"].get("generator", "feature-removal"),
            "oracle": oracle.get(task.name), "nop": nop.get(task.name),
            "f2p": cal.get("f2p"), "p2p": cal.get("p2p"),
            "flaky_excluded": len(cal.get("flaky_excluded", [])) if cal else None,
            "wrong_rejected": adv.get("killed"), "wrong_total": adv.get("mutants"),
            "partial_total": None, "partial_rejected": None,
            "hidden_tests": True, "separate_verifier": cfg["verifier"].get("environment_mode") == "separate",
            "provenance": bool(cfg["metadata"].get("source_commit")),
            "repro": None, "path": task,
        })

    # generated tasks
    for repo_dir in sorted(p for p in (ROOT / "tasks" / "generated").iterdir() if p.is_dir()):
        check = json.loads((repo_dir / "harbor-check.json").read_text()) \
            if (repo_dir / "harbor-check.json").exists() else {"results": {}}
        reports = {json.loads(p.read_text())["strategy"] + str(json.loads(p.read_text()).get("bugs_per_task", "")):
                   json.loads(p.read_text()) for p in repo_dir.glob("report-*.json")}
        for task in sorted(p for p in repo_dir.iterdir() if (p / "task.toml").exists()):
            cfg = tomllib.loads((task / "task.toml").read_text())
            m = cfg["metadata"]
            res = check["results"].get(task.name, {})
            bugs = "" if m["generator"] != "multi-bug" else str(m.get("change", "").count(";") + 1)
            report = reports.get(m["generator"] + bugs, {})
            repro_key = f"{repo_dir.name}:{m['generator']}" + (f":{bugs}bugs" if bugs else "") + f":seed{m['seed']}"
            rows.append({
                "task": task.name, "set": f"generated/{repo_dir.name}", "kind": m["generator"],
                "oracle": [res.get("oracle")] if "oracle" in res else None,
                "nop": [res.get("nop")] if "nop" in res else None,
                "f2p": m.get("f2p_tests"), "p2p": m.get("p2p_tests"),
                "flaky_excluded": (report.get("reference") or {}).get("flaky"),
                "wrong_rejected": m.get("adversarial_killed"), "wrong_total": m.get("adversarial_mutants"),
                # a k-bug task has 2^k - 2 partial fixes (every non-empty proper subset of bugs left in)
                "partial_total": (2 ** int(bugs) - 2) if m["generator"] == "multi-bug" else None,
                "partial_rejected": m.get("partial_fixes_rejected") if m["generator"] == "multi-bug" else None,
                "hidden_tests": m["generator"] == "test-writing",
                "separate_verifier": cfg["verifier"].get("environment_mode") == "separate",
                "provenance": bool(m.get("source_commit")),
                "repro": (repro.get(repro_key) or {}).get("identical"), "path": task,
            })
    return rows


def evaluate(row: dict) -> dict:
    def ok(value):
        return "pass" if value is True else "fail" if value is False else "unknown"
    kill = (row["wrong_rejected"] / row["wrong_total"]) if row["wrong_total"] else None
    pinned, offline = dockerfile_checks(row["path"])
    checks = {
        # rigor: construction
        "reference_passes": ok(None if row["oracle"] is None else all(r == 1 for r in row["oracle"])),
        "untouched_fails": ok(None if row["nop"] is None else all(r == 0 for r in row["nop"])),
        "change_is_asserted": ok(None if row["f2p"] is None else row["f2p"] > 0),
        "wrong_solutions_rejected_75": ok(None if kill is None else kill >= 0.75),
        "partial_fixes_rejected": "n/a" if row["partial_total"] is None else ok(row["partial_rejected"] == row["partial_total"]),
        "regression_guard": "n/a" if row["kind"] == "test-writing" else ok(None if row["p2p"] is None else row["p2p"] > 0),
        # reliability: evaluation
        "flaky_tests_excluded": ok(None if row["flaky_excluded"] is None else True),
        "separate_tamper_proof_verifier": ok(row["separate_verifier"]),
        "harbor_lint_clean": ok(harbor_lint_ok(row["path"])),
        # reproducibility: release
        "images_pinned_by_digest": ok(pinned),
        "offline_build": ok(offline),
        "provenance_recorded": ok(row["provenance"]),
        "deterministic_regeneration": "n/a" if row["set"] == "hand-made" else ok(row["repro"]),
    }
    return {"task": row["task"], "set": row["set"], "kind": row["kind"], "kill_rate": None if kill is None else round(kill, 3),
            "meets_95_floor": None if kill is None else kill >= 0.95, "checks": checks}


PILLARS = {
    "Rigor (construction)": ["reference_passes", "untouched_fails", "change_is_asserted",
                             "wrong_solutions_rejected_75", "partial_fixes_rejected", "regression_guard"],
    "Reliability (evaluation)": ["flaky_tests_excluded", "separate_tamper_proof_verifier", "harbor_lint_clean"],
    "Reproducibility (release)": ["images_pinned_by_digest", "offline_build", "provenance_recorded",
                                  "deterministic_regeneration"],
}
LABELS = {
    "reference_passes": "Reference solution scores 1 in Harbor (oracle agent)",
    "untouched_fails": "Untouched task scores 0 in Harbor (no-op agent)",
    "change_is_asserted": "Changed code is asserted by at least one fail-to-pass test",
    "wrong_solutions_rejected_75": "At least 75% of plausible wrong solutions are rejected",
    "partial_fixes_rejected": "Every partial fix is rejected (multi-bug)",
    "regression_guard": "Pass-to-pass regression suite guards the rest of the code",
    "flaky_tests_excluded": "Reference run twice; flaky tests excluded from grading",
    "separate_tamper_proof_verifier": "Grading in a separate sandbox that only receives the agent's output",
    "harbor_lint_clean": "`harbor lint` reports no findings",
    "images_pinned_by_digest": "Base images pinned by SHA-256 digest",
    "offline_build": "Builds offline (no package downloads in Dockerfiles)",
    "provenance_recorded": "Source repository and commit recorded",
    "deterministic_regeneration": "Same seed regenerates byte-identical tasks (repro_check)",
}


def main() -> int:
    rows = [evaluate(r) for r in collect()]
    (ROOT / "validation" / "rigor.json").write_text(json.dumps(rows, indent=2) + "\n")
    n = len(rows)
    lines = ["# Rigor certificate", "",
             "Every task in this repository was checked against the criteria below. Each check is computed "
             "by `factory/certify.py` from evidence on disk: Harbor runs, calibration and adversarial reports, "
             "generation reports, task files and recorded reproducibility checks. Checks are grouped by the "
             "three pillars proposed for trustworthy code benchmarks: rigor, reliability and reproducibility "
             "(see `docs/innovation-research.md`). A check with no evidence shows as *unknown*, never as passed.",
             "", f"**Tasks certified: {n}** ({sum(r['set'] == 'hand-made' for r in rows)} hand-made, "
             f"{sum(r['set'] != 'hand-made' for r in rows)} generated)", ""]
    for pillar, keys in PILLARS.items():
        lines += [f"## {pillar}", "", "| Check | Pass | Fail | Unknown | N/A |", "|---|---|---|---|---|"]
        for k in keys:
            vals = [r["checks"][k] for r in rows]
            lines.append(f"| {LABELS[k]} | {vals.count('pass')} | {vals.count('fail')} | "
                         f"{vals.count('unknown')} | {vals.count('n/a')} |")
        lines.append("")
    kills = [r for r in rows if r["kill_rate"] is not None]
    lines += ["## Wrong-solution kill rate", "",
              f"- **Acceptance gate:** every generated task must reject at least 75% of its plausible wrong "
              f"solutions. {sum(r['checks']['wrong_solutions_rejected_75'] == 'pass' for r in rows)}/{len(kills)} "
              f"tasks pass this gate.",
              f"- **Stricter 95% floor:** {sum(bool(r['meets_95_floor']) for r in kills)}/{len(kills)} tasks also "
              f"meet the 95% floor used to audit hardware-design benchmarks. Tasks below it are still accepted; "
              f"their surviving wrong solutions are listed in the generation reports.", ""]
    lines += ["## Contamination disclosure", "",
              "\"Unknown\" is a valid answer.", "",
              "| Leakage type | Status for this repository |", "|---|---|",
              "| Direct (test set public) | Yes, once this repository is public. Grading tests and hidden "
              "wrong solutions are in each task's `tests/` directory. |",
              "| Derivative (built from public code) | Yes. click, zod and jsoncpp are public, so reference "
              "solutions are upstream code a model may have memorised. Generated tasks are new *states* "
              "(injected defects, removed bodies) that do not exist upstream. |",
              "| Temporal (data before model cutoff) | Unknown. The pinned upstream commits are from Oct–Nov "
              "2026, but which models trained on them is not known. |",
              "| Acquired during evaluation | Possible. Agent sandboxes use `network_mode = \"public\"`, "
              "because Harbor's local Docker provider cannot enforce allowlists, so an agent could download "
              "upstream code. Run on a provider that enforces `allowlist` to close this. |", ""]
    lines += ["## Per-task results", "",
              "| Task | Set | Kind | Kill rate | All applicable checks pass |", "|---|---|---|---|---|"]
    for r in rows:
        applicable = [v for v in r["checks"].values() if v != "n/a"]
        status = "yes" if all(v == "pass" for v in applicable) else \
            "no (" + ", ".join(k for k, v in r["checks"].items() if v in ("fail", "unknown")) + ")"
        lines.append(f"| `{r['task']}` | {r['set']} | {r['kind']} | "
                     f"{'-' if r['kill_rate'] is None else r['kill_rate']} | {status} |")
    (ROOT / "RIGOR.md").write_text("\n".join(lines) + "\n")
    bad = [r["task"] for r in rows if any(v in ("fail", "unknown") for v in r["checks"].values())]
    print(f"[{'OK' if not bad else 'WARN'}] {n} tasks certified; {n - len(bad)} pass every applicable check")
    for t in bad:
        print("   needs attention:", t)
    return 0


if __name__ == "__main__":
    sys.exit(main())
