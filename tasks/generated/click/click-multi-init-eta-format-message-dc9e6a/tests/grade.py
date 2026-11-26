"""Turn /logs/verifier/results.json into Harbor rewards.

reward = 1 only when every test in f2p.txt passes (the feature works) and
every test in p2p.txt passes (nothing else regressed). The lists are recorded
by the factory: f2p = tests passing with the reference solution but not on the
untouched task; p2p = tests passing on both.
"""

from __future__ import annotations

import json
from pathlib import Path

LOGS = Path("/logs/verifier")
HERE = Path(__file__).parent


def read_list(name: str) -> list[str]:
    path = HERE / name
    return [" ".join(line.split()) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []


def main() -> None:
    results_file = LOGS / "results.json"
    results = json.loads(results_file.read_text()) if results_file.exists() else {}
    results = {" ".join(k.split()): v for k, v in results.items()}
    f2p, p2p = read_list("f2p.txt"), read_list("p2p.txt")

    f2p_passed = sum(results.get(t) == "passed" for t in f2p)
    p2p_broken = [t for t in p2p if results.get(t) != "passed"]
    feature_ok = bool(f2p) and f2p_passed == len(f2p)
    regression_ok = bool(p2p) and not p2p_broken

    rewards = {
        "reward": 1 if feature_ok and regression_ok else 0,
        "feature_pass_rate": round(f2p_passed / len(f2p), 4) if f2p else 0.0,
        "feature_tests": len(f2p),
        "regression_ok": 1 if regression_ok else 0,
        "p2p_tests": len(p2p),
        "p2p_broken": len(p2p_broken),
    }
    (LOGS / "reward.json").write_text(json.dumps(rewards))
    (LOGS / "p2p_broken.txt").write_text("\n".join(p2p_broken))
    print(json.dumps(rewards, indent=2))


if __name__ == "__main__":
    main()
