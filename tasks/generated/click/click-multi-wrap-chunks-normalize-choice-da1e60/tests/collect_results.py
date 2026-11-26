"""Convert pytest's JUnit XML into /logs/verifier/results.json ({test id: status})."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

LOGS = Path("/logs/verifier")


def main() -> None:
    results: dict[str, str] = {}
    report = LOGS / "junit.xml"
    if report.exists():
        for case in ET.parse(report).getroot().iter("testcase"):
            status = "passed"
            for child in case:
                if child.tag in ("failure", "error"):
                    status = "failed"
                    break
                if child.tag == "skipped":
                    status = "skipped"
            results[f"{case.get('classname') or 'hidden'}::{case.get('name')}"] = status
    (LOGS / "results.json").write_text(json.dumps(results, indent=1, sort_keys=True))
    print(f"{sum(s == 'passed' for s in results.values())}/{len(results)} test cases passed")


if __name__ == "__main__":
    main()
