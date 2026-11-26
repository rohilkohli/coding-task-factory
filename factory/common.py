"""Shared helpers for factory validation scripts.

Conventions every factory task follows:
  * environment/vendor/app-base.tar.(gz|br)  repository snapshot, prefix "app/",
                                              with the feature removed
  * solution/files/                           files the reference solution
                                              writes, relative to /app
  * task.toml artifacts[*].source             the only paths copied from the
                                              agent sandbox into the verifier
  * tests/test.sh                             writes /logs/verifier/results.json
                                              ({test id: status}) and reward.json
"""

from __future__ import annotations

import io
import json
import shutil
import subprocess
import tarfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def task_config(task: Path) -> dict:
    return tomllib.loads((task / "task.toml").read_text())


def artifact_sources(task: Path) -> list[str]:
    """Container paths of the agent's work that the verifier receives (e.g. /app/src)."""
    return [e["source"] if isinstance(e, dict) else e for e in task_config(task)["artifacts"]]


def artifact_rel_paths(task: Path) -> list[Path]:
    return [Path(src).relative_to("/app") for src in artifact_sources(task)]


def _open_archive(path: Path) -> tarfile.TarFile:
    if path.suffix == ".br":
        data = subprocess.run(
            ["node", "-e",
             'process.stdout.write(require("zlib").brotliDecompressSync(require("fs").readFileSync(process.argv[1])))',
             str(path)],
            check=True, capture_output=True,
        ).stdout
        return tarfile.open(fileobj=io.BytesIO(data))
    return tarfile.open(path)


def extract_tree(task: Path, dest: Path, with_solution: bool) -> Path:
    """Materialise /app as the agent would see it, optionally with the reference applied."""
    archive = next((task / "environment/vendor").glob("app-base.tar.*"))
    with _open_archive(archive) as tar:
        tar.extractall(dest, filter="data")
    app = dest / "app"
    if with_solution:
        overlay = task / "solution/files"
        for src in overlay.rglob("*"):
            if src.is_file():
                target = app / src.relative_to(overlay)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, target)
    return app


def build_verifier(task: Path) -> str:
    tag = f"factory-verifier-{task.name}"
    subprocess.run(["docker", "build", "-q", "-t", tag, str(task / "tests")],
                   check=True, capture_output=True, text=True)
    return tag


def run_verifier(image: str, task: Path, app: Path, logs_dir: Path,
                 timeout: int = 1800) -> dict:
    """Grade one candidate /app tree with the task's own verifier.

    Only the task's artifact paths are taken from `app` (exactly what Harbor
    would copy from the agent sandbox). Returns reward.json plus the per-test
    results under the key "_results"."""
    logs_dir.mkdir(parents=True, exist_ok=True)
    # Copy, because some graders rewrite test files inside the artifact tree.
    work = logs_dir.parent / f"{logs_dir.name}-artifacts"
    if work.exists():
        shutil.rmtree(work)
    mounts = []
    for rel in artifact_rel_paths(task):
        shutil.copytree(app / rel, work / rel, symlinks=True)
        mounts += ["-v", f"{work / rel}:/app/{rel}"]
    subprocess.run(
        ["docker", "run", "--rm", "--network", "none", *mounts,
         "-v", f"{logs_dir}:/logs/verifier",
         image, "bash", "/tests/test.sh"],
        check=False, capture_output=True, text=True, timeout=timeout,
    )
    reward_file = logs_dir / "reward.json"
    reward = json.loads(reward_file.read_text()) if reward_file.exists() else {"reward": None}
    results_file = logs_dir / "results.json"
    reward["_results"] = json.loads(results_file.read_text()) if results_file.exists() else {}
    return reward
