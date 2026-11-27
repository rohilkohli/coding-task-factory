"""Per-defect partial credit for multi-bug tasks.

Runs after the task's grader. For each injected defect, /tests/defects.json
lists the tests that the defect breaks on its own (tests broken by another
defect too are left out when the defect has tests of its own). A defect counts
as fixed when all of its tests pass. The binary `reward` is unchanged;
`defects_fixed`, `defects_total`, `partial_credit` and `defect_<i>_fixed` are
added to reward.json, and details go to partial_credit.json.
"""

import json
from pathlib import Path

LOGS = Path("/logs/verifier")
HERE = Path(__file__).parent


def norm(test_id: str) -> str:
    return " ".join(test_id.split())


def main() -> None:
    results_file, reward_file = LOGS / "results.json", LOGS / "reward.json"
    results = {norm(k): v for k, v in json.loads(results_file.read_text()).items()} if results_file.exists() else {}
    reward = json.loads(reward_file.read_text()) if reward_file.exists() else {"reward": 0}
    defects = json.loads((HERE / "defects.json").read_text())
    fixed = [int(bool(d["tests"]) and all(results.get(norm(t)) == "passed" for t in d["tests"])) for d in defects]
    reward.update({"defects_total": len(defects), "defects_fixed": sum(fixed),
                   "partial_credit": round(sum(fixed) / len(defects), 4) if defects else 0.0})
    for i, f in enumerate(fixed, 1):
        reward[f"defect_{i}_fixed"] = f
    reward_file.write_text(json.dumps(reward))
    (LOGS / "partial_credit.json").write_text(json.dumps(
        {"defects": [{**d, "fixed": bool(f)} for d, f in zip(defects, fixed)]}, indent=1))
    print(json.dumps({k: reward[k] for k in ("defects_fixed", "defects_total", "partial_credit")}))


if __name__ == "__main__":
    main()
