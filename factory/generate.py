"""Generate validated Harbor coding tasks from a repository.

Strategies
  bug-injection     one small realistic defect (operator / negation / literal
                    change) inside a function; the agent must find and fix it.
  function-removal  a function's body is replaced by a "not implemented" stub
                    (signature and docs kept); the agent must re-implement it.

For both, the reference solution is the pristine upstream code, and grading
uses the upstream test suite in a separate verifier sandbox.

Pipeline per candidate (every decision is recorded in the report):
  1. screen       run the verifier on the modified tree; F2P = tests that pass
                  on upstream (in both reference runs) but fail now; P2P = tests
                  that still pass. Reject if no test notices the change
                  ("undetected"), if too much of the suite breaks ("too-broad"),
                  or if nothing could be built/loaded ("build-failure").
  2. adversarial  apply K plausible wrong fixes (other mutations of the same
                  function on top of the reference) and grade them with the
                  task's F2P/P2P lists. Reject if the kill rate is below the
                  threshold: the tests are too weak to tell a wrong fix apart.
  3. package      write a complete Harbor task directory.

Usage:
  python factory/generate.py --repo click --strategy bug-injection --count 5 --seed 1
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import difflib
import gzip
import hashlib
import io
import json
import random
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

FACTORY = Path(__file__).resolve().parent
ROOT = FACTORY.parent
CACHE = ROOT / ".cache"
sys.path.insert(0, str(FACTORY))

from codeops import Function, Site, cpp_header_doc, find_functions, mutations_for, removal_stub  # noqa: E402
from common import _open_archive  # noqa: E402
from repos import REPOS, RepoConfig  # noqa: E402

LOCK = threading.Lock()
SHORT = {"bug-injection": "bug", "function-removal": "impl"}


def sha(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8", "surrogatepass"))
        h.update(b"\0")
    return h.hexdigest()


def log(msg: str) -> None:
    with LOCK:
        print(msg, flush=True)


# ----------------------------------------------------------------------------
# Upstream tree, verifier image, reference results

def upstream_tree(cfg: RepoConfig) -> Path:
    dest = CACHE / cfg.name / "upstream"
    if not (dest / "app").exists():
        dest.mkdir(parents=True, exist_ok=True)
        with _open_archive(FACTORY / "vendor" / cfg.name / f"app-upstream.{cfg.archive_ext}") as tar:
            tar.extractall(dest, filter="data")
    return dest / "app"


def verifier_image(cfg: RepoConfig) -> str:
    template = FACTORY / "templates" / cfg.name / "tests"
    vendor = FACTORY / "vendor" / cfg.name
    files = sorted(p for p in template.rglob("*") if p.is_file())
    digest = sha(*(f"{p.relative_to(template)}:{hashlib.sha256(p.read_bytes()).hexdigest()}" for p in files),
                 *(hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(vendor.rglob("*")) if p.is_file()))
    tag = f"factory-verifier-{cfg.name}:{digest[:12]}"
    if subprocess.run(["docker", "image", "inspect", tag], capture_output=True).returncode != 0:
        with tempfile.TemporaryDirectory() as ctx:
            ctx = Path(ctx)
            shutil.copytree(template, ctx, dirs_exist_ok=True)
            (ctx / "vendor").mkdir(exist_ok=True)
            shutil.copy2(vendor / f"app-upstream.{cfg.archive_ext}", ctx / "vendor")
            for extra in cfg.tests_vendor:
                src = vendor / extra
                (shutil.copytree if src.is_dir() else shutil.copy2)(src, ctx / "vendor" / extra)
            (ctx / "f2p.txt").write_text("")
            (ctx / "p2p.txt").write_text("")
            subprocess.run(["docker", "build", "-q", "-t", tag, str(ctx)], check=True, capture_output=True)
    return tag


def run_tests(cfg: RepoConfig, image: str, upstream: Path, edits: dict[str, str], key: str,
              timeout: float | None = None) -> dict[str, str]:
    """Per-test results for upstream + edits, graded by the repo's verifier (cached).

    A run that exceeds `timeout` (e.g. a mutation that creates an infinite loop)
    is killed and recorded as {"__timeout__": "failed"}."""
    cache = CACHE / cfg.name / "runs" / f"{sha(image, key)}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    timeout = timeout or cfg.resources["verifier_timeout"]
    name = f"factory-{cfg.name}-{sha(image, key)[:16]}"
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        mounts = []
        for source in cfg.artifacts:
            rel = Path(source).relative_to("/app")
            shutil.copytree(upstream / rel, tmp / "app" / rel, symlinks=True)
            mounts += ["-v", f"{tmp / 'app' / rel}:{source}"]
        for rel, text in edits.items():
            (tmp / "app" / rel).write_text(text)
        (tmp / "logs").mkdir()
        try:
            subprocess.run(["docker", "run", "--rm", "--name", name, "--network", "none", *mounts,
                            "-v", f"{tmp / 'logs'}:/logs/verifier", image, "bash", "/tests/test.sh"],
                           capture_output=True, timeout=timeout)
            results_file = tmp / "logs" / "results.json"
            results = json.loads(results_file.read_text()) if results_file.exists() else {}
        except subprocess.TimeoutExpired:
            subprocess.run(["docker", "rm", "-f", name], capture_output=True)
            results = {"__timeout__": "failed"}
    results = {" ".join(k.split()): v for k, v in results.items()}
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(results))
    return results


def passed(results: dict[str, str]) -> set[str]:
    return {t for t, s in results.items() if s == "passed"}


def grade(results: dict[str, str], f2p: list[str], p2p: list[str]) -> int:
    ok = passed(results)
    return int(all(t in ok for t in f2p) and all(t in ok for t in p2p))


# ----------------------------------------------------------------------------
# Candidates

@dataclass
class Candidate:
    id: str
    strategy: str
    file: str
    function: str
    line: int
    new_text: str
    description: str
    site: Site | None = None  # injected site (bug-injection)
    replacement: str = ""
    fn: Function | None = field(default=None, repr=False)


def source_files(cfg: RepoConfig, root: Path) -> list[str]:
    files = {str(p.relative_to(root)) for g in cfg.source_globs for p in root.glob(g)}
    return sorted(f for f in files if f not in cfg.source_exclude and ".test." not in f)


def body_lines(text: str, fn: Function) -> int:
    return sum(1 for line in text[fn.body_start:fn.body_end].splitlines()
               if line.strip() and not line.strip().startswith(("#", "//")))


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower().replace("$", "")).strip("-")[:40]


def interleave_by_file(fns: list[Function], rng: random.Random) -> list[Function]:
    groups: dict[str, list[Function]] = {}
    for fn in fns:
        groups.setdefault(fn.file, []).append(fn)
    order = sorted(groups)
    rng.shuffle(order)
    for f in order:
        rng.shuffle(groups[f])
    out = []
    while any(groups.values()):
        for f in order:
            if groups[f]:
                out.append(groups[f].pop())
    return out


def enumerate_candidates(cfg: RepoConfig, strategy: str, fns: list[Function], texts: dict[str, str],
                         rng: random.Random):
    for fn in interleave_by_file(fns, rng):
        text = texts[fn.file]
        if strategy == "bug-injection":
            sites = [s for s in fn.sites if mutations_for(s)]
            if not sites:
                continue
            site = rng.choice(sites)
            repl = rng.choice(mutations_for(site))
            new_text = text[:site.start] + repl + text[site.end:]
            desc = f"`{site.text}` -> `{repl}`" if repl else f"removed `{site.text.strip()}`"
            cid = f"{cfg.name}-bug-{slug(fn.name)}-{sha(fn.file, new_text)[:6]}"
            yield Candidate(cid, strategy, fn.file, fn.name, fn.line, new_text, desc, site, repl, fn)
        elif strategy == "function-removal":
            n = body_lines(text, fn)
            if not 3 <= n <= 60 or fn.name.split(".")[-1].startswith("__"):
                continue
            new_text = removal_stub(cfg.language, fn, text)
            cid = f"{cfg.name}-impl-{slug(fn.name)}-{sha(fn.file, new_text)[:6]}"
            yield Candidate(cid, strategy, fn.file, fn.name, fn.line, new_text, f"body removed ({n} lines)",
                            fn=fn)
        else:
            raise ValueError(strategy)


def wrong_fixes(cand: Candidate, upstream_text: str, rng: random.Random, k: int) -> list[tuple[str, str]]:
    """Plausible wrong solutions: the reference with one other mutation in the same function."""
    options = []
    for s in cand.fn.sites:
        for repl in mutations_for(s):
            if cand.site is not None and s.start == cand.site.start:
                continue  # handled below
            options.append((f"{s.text.strip()} -> {repl or '(removed)'} @ offset {s.start}",
                            upstream_text[:s.start] + repl + upstream_text[s.end:]))
    if cand.site is not None:  # other "fixes" at the injected site
        for repl in mutations_for(cand.site):
            if repl != cand.replacement:
                options.append((f"injected site {cand.site.text.strip()} -> {repl or '(removed)'}",
                                upstream_text[:cand.site.start] + repl + upstream_text[cand.site.end:]))
    rng.shuffle(options)
    return options[:k]


# ----------------------------------------------------------------------------
# Packaging

def _deterministic_tar(tree: Path, edits: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.PAX_FORMAT) as tar:
        paths = sorted(tree.rglob("*"), key=lambda p: str(p.relative_to(tree)))
        for p in [tree] + paths:
            rel = p.relative_to(tree.parent)
            info = tar.gettarinfo(str(p), arcname=str(rel))
            info.mtime, info.uid, info.gid, info.uname, info.gname = 0, 0, 0, "", ""
            relapp = str(p.relative_to(tree))
            if p.is_file() and not p.is_symlink() and relapp in edits:
                data = edits[relapp].encode()
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
            elif p.is_file() and not p.is_symlink():
                with open(p, "rb") as fh:
                    tar.addfile(info, fh)
            else:
                tar.addfile(info)
    return buf.getvalue()


def write_archive(cfg: RepoConfig, upstream: Path, edits: dict[str, str], dest: Path) -> None:
    raw = _deterministic_tar(upstream, edits)
    if cfg.archive_ext == "tar.gz":
        with open(dest, "wb") as fh, gzip.GzipFile(fileobj=fh, mode="wb", mtime=0, filename="") as gz:
            gz.write(raw)
    else:
        with tempfile.NamedTemporaryFile(suffix=".tar") as tmp:
            tmp.write(raw)
            tmp.flush()
            subprocess.run(["node", str(FACTORY / "brotli_tar.mjs"), tmp.name, str(dest)], check=True)


def display_tests(tests: list[str], limit: int = 5) -> list[str]:
    seen, out = set(), []
    for t in sorted(tests):
        # vitest reports type-level checks as "<file> > <file> <name>"; show one form
        m = re.match(r"^(\S+) > \1 (.*)$", t)
        key = f"{m.group(1)} > {m.group(2)}" if m else t
        if key not in seen:
            seen.add(key)
            out.append(key)
    return out[:limit] + ([f"... and {len(out) - limit} more"] if len(out) > limit else [])


def instruction(cfg: RepoConfig, cand: Candidate, f2p: list[str], upstream_text: str) -> str:
    src_dirs = sorted({str(Path(g).parent) for g in cfg.source_globs})
    where = ", ".join(f"`/app/{d}`" for d in src_dirs)
    failing = "\n".join(f"- `{t}`" if not t.startswith("...") else f"- {t}" for t in display_tests(f2p))
    if cand.strategy == "bug-injection":
        return (
            f"A regression has been introduced into the {cfg.project} library in `/app` "
            f"(library source under {where}). Some behaviour no longer matches what the project's own test "
            f"suite expects. These tests currently fail:\n\n{failing}\n\n"
            "Find the defect in the library source and fix it. Do not modify the tests: grading uses the "
            "original test suite, and every test that passed before the regression must still pass.\n\n"
            f"{cfg.test_hint}\n"
        )
    fn = cand.fn
    lang = {"python": "python", "typescript": "ts", "cpp": "cpp"}[cfg.language]
    signature = upstream_text[fn.start:fn.body_start].rstrip()
    doc = fn.doc.strip()
    if cfg.language == "cpp" and not doc:
        doc = cpp_header_doc(CACHE / cfg.name / "upstream" / "app", fn)
    if cfg.language != "python" and doc:
        signature = doc + "\n" + signature
    if cfg.language != "python":
        signature += " ... }"
    return (
        f"In the {cfg.project} library in `/app`, the implementation of `{fn.name}` in `{fn.file}` has been "
        "removed. Its body is now a stub that fails with \"not implemented\". Re-implement it so it behaves "
        f"the way the rest of the codebase and its documentation expect.\n\nCurrent signature and "
        f"documentation:\n\n```{lang}\n{signature}\n```\n\n"
        f"The project's test suite exercises this code. These tests currently fail:\n\n{failing}\n\n"
        "Make them pass without modifying any tests, and keep the rest of the test suite passing.\n\n"
        f"{cfg.test_hint}\n"
    )


def difficulty(cand: Candidate, f2p: list[str], upstream_text: str) -> tuple[str, str]:
    if cand.strategy == "function-removal":
        n = body_lines(upstream_text, cand.fn)
        level = "easy" if n <= 8 else "medium" if n <= 25 else "hard"
        return level, f"Re-implement a {n}-line function body from its signature, docs and call sites."
    n = len(display_tests(f2p, limit=10**6))
    level = "hard" if n <= 2 else "medium" if n <= 10 else "easy"
    return level, f"Single-token defect ({cand.description}) detected by {n} failing test(s); hint: failing tests only."


def toml_str(value) -> str:
    return json.dumps(value) if isinstance(value, str) else str(value).lower() if isinstance(value, bool) else str(value)


def package(cfg: RepoConfig, cand: Candidate, f2p: list[str], p2p: list[str], adv: dict,
            upstream: Path, out_root: Path, seed: int) -> Path:
    task = out_root / cand.id
    if task.exists():
        shutil.rmtree(task)
    upstream_text = (upstream / cand.file).read_text()
    edits = {cand.file: cand.new_text}

    # environment
    shutil.copytree(FACTORY / "templates" / cfg.name / "environment", task / "environment")
    (task / "environment" / "vendor").mkdir()
    write_archive(cfg, upstream, edits, task / "environment" / "vendor" / f"app-base.{cfg.archive_ext}")
    for extra in cfg.env_vendor:
        src = FACTORY / "vendor" / cfg.name / extra
        (shutil.copytree if src.is_dir() else shutil.copy2)(src, task / "environment" / "vendor" / extra)

    # verifier
    shutil.copytree(FACTORY / "templates" / cfg.name / "tests", task / "tests")
    (task / "tests" / "vendor").mkdir()
    shutil.copy2(FACTORY / "vendor" / cfg.name / f"app-upstream.{cfg.archive_ext}", task / "tests" / "vendor")
    for extra in cfg.tests_vendor:
        src = FACTORY / "vendor" / cfg.name / extra
        (shutil.copytree if src.is_dir() else shutil.copy2)(src, task / "tests" / "vendor" / extra)
    (task / "tests" / "f2p.txt").write_text("\n".join(f2p) + "\n")
    (task / "tests" / "p2p.txt").write_text("\n".join(p2p) + "\n")

    # reference solution
    sol = task / "solution" / "files" / cand.file
    sol.parent.mkdir(parents=True)
    sol.write_text(upstream_text)
    (task / "solution" / "solve.sh").write_text(
        "#!/bin/bash\n# Reference solution: the pristine upstream file\n"
        f"# ({cfg.url} @ {cfg.commit}).\nset -euo pipefail\n"
        f"cp /solution/files/{cand.file} /app/{cand.file}\n")
    (task / "solution" / "solve.sh").chmod(0o755)
    (task / "tests" / "test.sh").chmod(0o755)

    (task / "instruction.md").write_text(instruction(cfg, cand, f2p, upstream_text))
    diff = difflib.unified_diff(upstream_text.splitlines(keepends=True), cand.new_text.splitlines(keepends=True),
                                f"a/{cand.file}", f"b/{cand.file}")
    (task / "task_edit.diff").write_text("".join(diff))

    level, why = difficulty(cand, f2p, upstream_text)
    r = cfg.resources
    meta = {
        "generator": cand.strategy, "seed": seed, "source_repo": cfg.url, "source_commit": cfg.commit,
        "language": cfg.language, "file": cand.file, "function": cand.function, "line": cand.line,
        "change": cand.description, "f2p_tests": len(f2p), "p2p_tests": len(p2p),
        "adversarial_mutants": adv["mutants"], "adversarial_killed": adv["killed"],
        "difficulty": level, "difficulty_explanation": why,
        "category": "bug-fix" if cand.strategy == "bug-injection" else "feature-implementation",
    }
    artifacts = ", ".join(f'{{ source = "{a}" }}' for a in cfg.artifacts)
    desc = (f"Fix a regression injected into {cand.function} ({cand.file})" if cand.strategy == "bug-injection"
            else f"Re-implement {cand.function} ({cand.file})")
    toml = [
        'schema_version = "1.4"', f"artifacts = [{artifacts}]", "", "[task]",
        f'name = "coding-task-factory/{cand.id}"', 'version = "1.0.0"', f"description = {toml_str(desc)}",
        "authors = []", f'keywords = ["{cfg.language}", "{cfg.name}", "{meta["category"]}", "generated"]', "",
        "[metadata]", *[f"{k} = {toml_str(v)}" for k, v in meta.items()], "",
        "[verifier]", f"timeout_sec = {float(r['verifier_timeout'])}", 'environment_mode = "separate"', "",
        "[verifier.environment]", "build_timeout_sec = 900.0", 'os = "linux"',
        f"cpus = {r['cpus']}", f"memory_mb = {r['memory_mb']}", "",
        "[agent]", "timeout_sec = 1800.0", "",
        "[environment]", 'network_mode = "public"', "build_timeout_sec = 900.0", 'os = "linux"',
        f"cpus = {r['cpus']}", f"memory_mb = {r['memory_mb']}", "",
    ]
    (task / "task.toml").write_text("\n".join(toml))
    return task


# ----------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True, choices=sorted(REPOS))
    ap.add_argument("--strategy", required=True, choices=sorted(SHORT))
    ap.add_argument("--count", type=int, default=5, help="tasks to produce")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--max-attempts", type=int, default=0, help="candidates to try (default 8x count)")
    ap.add_argument("--adversarial", type=int, default=6, help="wrong fixes tried per task")
    ap.add_argument("--min-kill-rate", type=float, default=0.75)
    ap.add_argument("--max-f2p-fraction", type=float, default=0.25)
    ap.add_argument("--workers", type=int, default=0)
    ap.add_argument("--out", type=Path, default=ROOT / "tasks" / "generated")
    args = ap.parse_args()

    cfg = REPOS[args.repo]
    started = time.time()
    rng = random.Random(f"{cfg.name}:{args.strategy}:{args.seed}")
    max_attempts = args.max_attempts or args.count * 8
    workers = args.workers or cfg.workers

    upstream = upstream_tree(cfg)
    image = verifier_image(cfg)
    log(f"[..] {cfg.name}: verifier image {image}")
    t0 = time.time()
    ref1 = run_tests(cfg, image, upstream, {}, "reference-1")
    ref_secs = time.time() - t0
    ref2 = run_tests(cfg, image, upstream, {}, "reference-2")  # separate key, so a real second run
    timing_file = CACHE / cfg.name / "reference-seconds.json"
    if ref_secs > 5 or not timing_file.exists():  # a real run (not a cache hit): remember its duration
        timing_file.write_text(json.dumps({"seconds": ref_secs}))
    ref_secs = json.loads(timing_file.read_text())["seconds"]
    run_timeout = max(60.0, 3 * ref_secs + 30)  # parallel runs are slower; infinite loops are not
    stable = passed(ref1) & passed(ref2)
    flaky = passed(ref1) ^ passed(ref2)
    log(f"[..] reference: {len(ref1)} tests, {len(stable)} stable passes, {len(flaky)} flaky; "
        f"run timeout {run_timeout:.0f}s")
    if not stable:
        log("[FAIL] reference solution passes no tests; check the verifier template")
        return 1

    files = source_files(cfg, upstream)
    texts = {f: (upstream / f).read_text() for f in files}
    ts_module = CACHE / "zod" / "node_modules" / "typescript" if cfg.language == "typescript" else None
    fns = find_functions(cfg.language, upstream, files, ts_module)
    log(f"[..] {len(files)} source files, {len(fns)} functions, {sum(len(f.sites) for f in fns)} mutation sites")

    candidates = enumerate_candidates(cfg, args.strategy, fns, texts, rng)
    adv_rng_seed = f"{cfg.name}:{args.strategy}:{args.seed}:adversarial"
    records: list[dict] = []
    accepted: list[tuple[Candidate, list[str], list[str], dict]] = []

    def evaluate(cand: Candidate, index: int) -> dict:
        rec = {"index": index, "id": cand.id, "file": cand.file, "function": cand.function, "line": cand.line,
               "change": cand.description}
        results = run_tests(cfg, image, upstream, {cand.file: cand.new_text}, f"cand:{cand.file}:{cand.new_text}",
                            run_timeout)
        if "__timeout__" in results:
            return {**rec, "status": "rejected", "reason": "hangs"}
        if not results:
            return {**rec, "status": "rejected", "reason": "build-failure"}
        now = passed(results)
        f2p = sorted(stable - now)
        p2p = sorted(stable & now)
        rec.update(f2p=len(f2p), p2p=len(p2p))
        if not f2p:
            return {**rec, "status": "rejected", "reason": "undetected"}
        if len(f2p) > args.max_f2p_fraction * len(stable):
            return {**rec, "status": "rejected", "reason": "too-broad"}
        fixes = wrong_fixes(cand, texts[cand.file], random.Random(f"{adv_rng_seed}:{cand.id}"), args.adversarial)
        if not fixes:
            return {**rec, "status": "rejected", "reason": "no-adversarial-sites"}
        killed, survivors = 0, []
        for desc, text in fixes:
            res = run_tests(cfg, image, upstream, {cand.file: text}, f"adv:{cand.file}:{text}", run_timeout)
            if grade(res, f2p, p2p) == 0:
                killed += 1
            else:
                survivors.append(desc)
        rate = killed / len(fixes)
        adv = {"mutants": len(fixes), "killed": killed, "kill_rate": round(rate, 3), "survivors": survivors}
        rec.update(adversarial=adv)
        if rate < args.min_kill_rate:
            return {**rec, "status": "rejected", "reason": "weak-tests"}
        rec["_payload"] = (cand, f2p, p2p, adv)
        return {**rec, "status": "accepted"}

    attempts = 0
    with cf.ThreadPoolExecutor(max_workers=workers) as pool:
        pending: dict[cf.Future, Candidate] = {}
        exhausted = False
        while True:
            while not exhausted and len(pending) < workers and attempts < max_attempts \
                    and len(accepted) + len(pending) < args.count + workers:
                if len(accepted) >= args.count:
                    break
                cand = next(candidates, None)
                if cand is None:
                    exhausted = True
                    break
                attempts += 1
                pending[pool.submit(evaluate, cand, attempts)] = cand
            if not pending:
                break
            done, _ = cf.wait(pending, return_when=cf.FIRST_COMPLETED)
            for fut in done:
                pending.pop(fut)
                rec = fut.result()
                if rec["status"] == "accepted":
                    accepted.append((rec["index"], rec["_payload"]))
                records.append(rec)
                extra = f" f2p={rec.get('f2p')} kill={rec.get('adversarial', {}).get('kill_rate')}" \
                    if "f2p" in rec else ""
                log(f"[{'OK' if rec['status'] == 'accepted' else '--'}] {rec['id']:<60} {rec['status']}"
                    f"{' (' + rec.get('reason', '') + ')' if rec.get('reason') else ''}{extra}")
            if len(accepted) >= args.count and not pending:
                break

    # Keep the first `count` accepted candidates in enumeration (seed) order, so
    # the result never depends on which parallel run finished first.
    accepted.sort(key=lambda t: t[0])
    keep = {idx for idx, _ in accepted[:args.count]}
    for rec in records:
        rec.pop("_payload", None)
        if rec["status"] == "accepted" and rec["index"] not in keep:
            rec.update(status="surplus", reason="target count already reached")
    accepted = [payload for idx, payload in accepted if idx in keep]

    out_root = args.out / cfg.name
    out_root.mkdir(parents=True, exist_ok=True)
    for cand, f2p, p2p, adv in accepted:
        package(cfg, cand, f2p, p2p, adv, upstream, out_root, args.seed)

    funnel: dict[str, int] = {}
    for rec in records:
        key = rec["status"] if rec["status"] != "rejected" else f"rejected:{rec['reason']}"
        funnel[key] = funnel.get(key, 0) + 1
    report = {
        "repo": cfg.name, "strategy": args.strategy, "seed": args.seed, "count_requested": args.count,
        "candidates_tried": attempts, "accepted": len(accepted), "funnel": dict(sorted(funnel.items())),
        "reference": {"tests": len(ref1), "stable_passing": len(stable), "flaky": len(flaky)},
        "thresholds": {"min_kill_rate": args.min_kill_rate, "max_f2p_fraction": args.max_f2p_fraction,
                       "adversarial_per_task": args.adversarial},
        "tasks": [c.id for c, *_ in accepted],
        "elapsed_sec": round(time.time() - started, 1),
        "candidates": sorted(records, key=lambda r: r["index"]),
    }
    report_path = out_root / f"report-{SHORT[args.strategy]}-seed{args.seed}.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    log(f"[OK] {len(accepted)}/{args.count} tasks from {attempts} candidates in {report['elapsed_sec']}s; "
        f"funnel {report['funnel']}; report {report_path.relative_to(ROOT)}")
    return 0 if len(accepted) == args.count else 2


if __name__ == "__main__":
    sys.exit(main())
