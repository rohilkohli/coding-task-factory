"""Generate validated Harbor coding tasks from a repository.

Strategies
  bug-injection     one small realistic defect (operator / negation / literal
                    change) inside a function; the agent must find and fix it.
  function-removal  a function's body is replaced by a "not implemented" stub
                    (signature and docs kept); the agent must re-implement it.
  multi-bug         2-3 individually validated bug-injection defects in
                    different functions (preferably different files) combined
                    into one task. Patch fragmentation is the strongest
                    predictor of task difficulty in the literature, so this is
                    the "hard" tier. Every partial fix must still fail.

The reference solution is always the pristine upstream code, and grading uses
the upstream test suite in a separate verifier sandbox.

Pipeline per candidate (every decision is recorded in the report):
  1. screen       run the verifier on the modified tree; F2P = tests that pass
                  on upstream (in both reference runs) but fail now; P2P = tests
                  that still pass. Reject if no test notices the change
                  ("undetected"), if too much of the suite breaks ("too-broad"),
                  if nothing could be built/loaded ("build-failure") or if the
                  run exceeds a timeout ("hangs").
  2. adversarial  grade plausible wrong fixes with the task's F2P/P2P lists:
                  operator mutations and statement deletions in the affected
                  functions, applied on top of the reference (plus, for
                  multi-bug, every partial fix). Reject if fewer than
                  --min-wrong-fixes can be built, if any partial fix passes
                  ("masked-bugs"), or if the kill rate is below the threshold
                  ("weak-tests").
  3. package      write a complete Harbor task directory with a static
                  difficulty score.

Usage:
  python factory/generate.py --repo click --strategy bug-injection --count 5 --seed 1
  python factory/generate.py --repo click --strategy multi-bug --bugs 2 --count 2 --seed 1
"""

from __future__ import annotations

import argparse
import ast
import concurrent.futures as cf
import difflib
import gzip
import hashlib
import io
import itertools
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
SHORT = {"bug-injection": "bug", "function-removal": "impl", "multi-bug": "multi", "test-writing": "test"}


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
# Upstream tree, verifier image, test runs

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


def edits_key(prefix: str, files: dict[str, str]) -> str:
    # single-file keys keep the original format so cached runs stay valid
    if len(files) == 1:
        (rel, text), = files.items()
        return f"{prefix}:{rel}:{text}"
    return f"{prefix}:" + json.dumps(sorted(files.items()))


def run_tests(cfg: RepoConfig, image: str, upstream: Path, files: dict[str, str], key: str,
              timeout: float | None = None) -> dict[str, str]:
    """Per-test results for upstream + modified files, graded by the repo's verifier (cached).

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
        for rel, text in files.items():
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
class Edit:
    file: str
    start: int  # offsets into the upstream text
    end: int
    new: str


@dataclass
class Candidate:
    id: str
    strategy: str
    edits: list[Edit]
    functions: list[Function]
    description: str
    injected: list[tuple[Site, str]] = field(default_factory=list)  # (site, replacement) for bug kinds
    parts: list["Candidate"] = field(default_factory=list)  # components of a multi-bug task

    @property
    def files(self) -> list[str]:
        return sorted({e.file for e in self.edits})

    @property
    def function_names(self) -> str:
        return ", ".join(fn.name for fn in self.functions)


def apply_edits(texts: dict[str, str], edits: list[Edit]) -> dict[str, str]:
    """Modified file texts; edits within a file must not overlap."""
    out: dict[str, str] = {}
    for rel in sorted({e.file for e in edits}):
        text = texts[rel]
        last = len(text) + 1
        for e in sorted((e for e in edits if e.file == rel), key=lambda e: e.start, reverse=True):
            if e.end > last:
                raise ValueError(f"overlapping edits in {rel}")
            text = text[:e.start] + e.new + text[e.end:]
            last = e.start
        out[rel] = text
    return out


def source_files(cfg: RepoConfig, root: Path) -> list[str]:
    files = {str(p.relative_to(root)) for g in cfg.source_globs for p in root.glob(g)}
    return sorted(f for f in files if f not in cfg.source_exclude and ".test." not in f)


def body_lines(text: str, fn: Function) -> int:
    return sum(1 for line in text[fn.body_start:fn.body_end].splitlines()
               if line.strip() and not line.strip().startswith(("#", "//")))


def slug(name: str, limit: int = 40) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower().replace("$", "")).strip("-")[:limit].strip("-")


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
            yield Candidate(cid, strategy, [Edit(fn.file, site.start, site.end, repl)], [fn], desc,
                            injected=[(site, repl)])
        elif strategy == "function-removal":
            n = body_lines(text, fn)
            if not 3 <= n <= 60 or fn.name.split(".")[-1].startswith("__"):
                continue
            new_text = removal_stub(cfg.language, fn, text)
            cid = f"{cfg.name}-impl-{slug(fn.name)}-{sha(fn.file, new_text)[:6]}"
            yield Candidate(cid, strategy, [Edit(fn.file, 0, len(text), new_text)], [fn],
                            f"body removed ({n} lines)")
        else:
            raise ValueError(strategy)


def _valid(cfg: RepoConfig, rel: str, text: str) -> bool:
    if cfg.language == "python":
        try:
            ast.parse(text)
        except SyntaxError:
            return False
    return True


def wrong_fixes(cfg: RepoConfig, cand: Candidate, texts: dict[str, str], rng: random.Random,
                k: int) -> tuple[list[tuple[str, dict[str, str]]], list[tuple[str, dict[str, str]]]]:
    """(must_kill, sampled) plausible wrong solutions.

    must_kill: for multi-bug tasks, every partial fix (some injected bugs left in).
    sampled:   up to k of: the reference with one other operator mutation or one
               statement deletion in an affected function, or a different
               "fix" at an injected site. Operator and deletion options are
               interleaved so both kinds are represented."""
    must = []
    if cand.parts:
        n = len(cand.parts)
        for size in range(1, n):
            for remaining in itertools.combinations(range(n), size):
                edits = [e for i in remaining for e in cand.parts[i].edits]
                names = " + ".join(cand.parts[i].functions[0].name for i in remaining)
                must.append((f"partial fix (still broken: {names})", apply_edits(texts, edits)))

    injected_starts = {s.start for s, _ in cand.injected}
    ops, dels = [], []
    for fn in cand.functions:
        upstream_text = texts[fn.file]
        for s in fn.sites:
            for repl in mutations_for(s):
                if s.start in injected_starts and any(repl == r for st, r in cand.injected if st.start == s.start):
                    continue  # that is the injected bug itself, not a wrong fix
                new = upstream_text[:s.start] + repl + upstream_text[s.end:]
                where = "injected site" if s.start in injected_starts else f"offset {s.start}"
                ops.append((f"{fn.name}: {s.text.strip()} -> {repl or '(removed)'} @ {where}", {fn.file: new}))
        for s in fn.deletions:
            repl = mutations_for(s)[0]
            new = upstream_text[:s.start] + repl + upstream_text[s.end:]
            first = s.text.strip().splitlines()[0][:60]
            dels.append((f"{fn.name}: deleted `{first}`", {fn.file: new}))
    rng.shuffle(ops)
    rng.shuffle(dels)
    sampled = []
    for a, b in itertools.zip_longest(ops, dels):
        for opt in (a, b):
            if opt is not None and len(sampled) < k and all(_valid(cfg, r, t) for r, t in opt[1].items()):
                sampled.append(opt)
        if len(sampled) >= k:
            break
    return must, sampled


# ----------------------------------------------------------------------------
# Difficulty (static, pre-hoc)

def change_features(cand: Candidate, texts: dict[str, str], f2p: list[str]) -> dict:
    """Static features that predict agent difficulty: patch fragmentation
    (locations), files, size, and how directly failing tests point at it."""
    new_texts = apply_edits(texts, cand.edits)
    locations = lines = 0
    for rel, new in new_texts.items():
        sm = difflib.SequenceMatcher(None, texts[rel].splitlines(), new.splitlines(), autojunk=False)
        for tag, i1, i2, _, _ in sm.get_opcodes():
            if tag != "equal":
                locations += 1
                lines += max(i2 - i1, 1)
    if cand.strategy == "function-removal":
        # one function to re-implement; the stub's helper include (C++) is not a location
        locations, lines = 1, body_lines(texts[cand.functions[0].file], cand.functions[0])
    signal = len(display_tests(f2p, limit=10 ** 6))
    return {"locations": locations, "files": len(new_texts), "lines": lines, "failing_tests": signal}


def difficulty(cand: Candidate, feats: dict) -> tuple[str, int, str]:
    """Points: fragmentation dominates (2+ locations), then cross-file changes,
    amount of code to write, and the failure signal (a strong signal only makes a
    single-location change easier). <=0 easy, 1-2 medium, >=3 hard."""
    score = {1: 0, 2: 2}.get(feats["locations"], 3 if feats["locations"] >= 3 else 0)
    score += 1 if feats["files"] > 1 else 0
    if cand.strategy == "function-removal":
        score += 1 if feats["lines"] <= 8 else 2 if feats["lines"] <= 25 else 3
    elif feats["lines"] > 2:
        score += 1
    if feats["failing_tests"] <= 2:
        score += 1  # weak signal: hard to localise
    elif feats["failing_tests"] >= 30 and feats["locations"] == 1:
        score -= 1  # many failures pointing at a single change make it easy to find
    level = "easy" if score <= 0 else "medium" if score <= 2 else "hard"
    why = (f"Static estimate (score {score}): {feats['locations']} change location(s) in {feats['files']} file(s), "
           f"{feats['lines']} line(s) to fix or write, {feats['failing_tests']} failing test(s) as signal.")
    return level, score, why


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
        existing = {str(p.relative_to(tree)) for p in paths}
        added_dirs: set[str] = set()
        for rel in sorted(r for r in edits if r not in existing):
            parts = Path(rel).parts
            for i in range(1, len(parts)):
                d = "/".join(parts[:i])
                if d not in existing and d not in added_dirs:
                    info = tarfile.TarInfo(f"{tree.name}/{d}")
                    info.type, info.mode = tarfile.DIRTYPE, 0o755
                    tar.addfile(info)
                    added_dirs.add(d)
            data = edits[rel].encode()
            info = tarfile.TarInfo(f"{tree.name}/{rel}")
            info.size, info.mode = len(data), 0o644
            tar.addfile(info, io.BytesIO(data))
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


def instruction(cfg: RepoConfig, cand: Candidate, f2p: list[str], texts: dict[str, str]) -> str:
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
    if cand.strategy == "multi-bug":
        return (
            f"Several regressions ({len(cand.parts)}) have been introduced into the {cfg.project} library in "
            f"`/app` (library source under {where}). They are independent defects in different parts of the "
            f"library. These tests currently fail:\n\n{failing}\n\n"
            "Find and fix every defect in the library source. Fixing only some of them is not enough: all of "
            "the tests above must pass. Do not modify the tests; grading uses the original test suite, and "
            "every test that passed before the regressions must still pass.\n\n"
            f"{cfg.test_hint}\n"
        )
    fn = cand.functions[0]
    upstream_text = texts[fn.file]
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


def add_partial_credit(cfg: RepoConfig, task: Path, defects: list[dict]) -> None:
    """Per-defect partial credit, added to this task's verifier only (the shared
    screening image is untouched, so cached test runs stay valid)."""
    script = "partial_credit.mjs" if cfg.language == "typescript" else "partial_credit.py"
    runner = "node" if cfg.language == "typescript" else "python3"
    shutil.copy2(FACTORY / "templates" / "common" / script, task / "tests" / script)
    (task / "tests" / "defects.json").write_text(json.dumps(defects, indent=1) + "\n")
    dockerfile = task / "tests" / "Dockerfile"
    lines = dockerfile.read_text().splitlines()
    last_copy = max(i for i, line in enumerate(lines) if line.startswith("COPY ") and "/tests/" in line)
    lines.insert(last_copy + 1, f"COPY defects.json {script} /tests/")
    dockerfile.write_text("\n".join(lines) + "\n")
    test_sh = task / "tests" / "test.sh"
    test_sh.write_text(test_sh.read_text().rstrip("\n") + f"\n\n# Per-defect partial credit (multi-bug tasks)\n{runner} /tests/{script}\n")


def toml_str(value) -> str:
    return json.dumps(value) if isinstance(value, str) else str(value).lower() if isinstance(value, bool) else str(value)


def package(cfg: RepoConfig, cand: Candidate, f2p: list[str], p2p: list[str], adv: dict,
            upstream: Path, texts: dict[str, str], out_root: Path, seed: int) -> Path:
    task = out_root / cand.id
    if task.exists():
        shutil.rmtree(task)
    new_files = apply_edits(texts, cand.edits)

    # environment
    shutil.copytree(FACTORY / "templates" / cfg.name / "environment", task / "environment")
    (task / "environment" / "vendor").mkdir()
    write_archive(cfg, upstream, new_files, task / "environment" / "vendor" / f"app-base.{cfg.archive_ext}")
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
    if adv.get("defects"):
        add_partial_credit(cfg, task, adv["defects"])

    # reference solution: the pristine upstream files
    copies = []
    for rel in new_files:
        sol = task / "solution" / "files" / rel
        sol.parent.mkdir(parents=True, exist_ok=True)
        sol.write_text(texts[rel])
        copies.append(f"cp /solution/files/{rel} /app/{rel}")
    (task / "solution" / "solve.sh").write_text(
        "#!/bin/bash\n# Reference solution: the pristine upstream file(s)\n"
        f"# ({cfg.url} @ {cfg.commit}).\nset -euo pipefail\n" + "\n".join(copies) + "\n")
    (task / "solution" / "solve.sh").chmod(0o755)
    (task / "tests" / "test.sh").chmod(0o755)

    (task / "instruction.md").write_text(instruction(cfg, cand, f2p, texts))
    diff = "".join("".join(difflib.unified_diff(texts[rel].splitlines(keepends=True),
                                                 new_files[rel].splitlines(keepends=True),
                                                 f"a/{rel}", f"b/{rel}")) for rel in sorted(new_files))
    (task / "task_edit.diff").write_text(diff)

    feats = change_features(cand, texts, f2p)
    level, score, why = difficulty(cand, feats)
    r = cfg.resources
    category = "feature-implementation" if cand.strategy == "function-removal" else "bug-fix"
    meta = {
        "generator": cand.strategy, "seed": seed, "source_repo": cfg.url, "source_commit": cfg.commit,
        "language": cfg.language, "file": ", ".join(cand.files), "function": cand.function_names,
        "line": cand.functions[0].line, "change": cand.description,
        "f2p_tests": len(f2p), "p2p_tests": len(p2p),
        "adversarial_mutants": adv["mutants"], "adversarial_killed": adv["killed"],
        "partial_fixes_rejected": adv.get("partial_killed", 0),
        "difficulty": level, "difficulty_score": score, "difficulty_explanation": why,
        "change_locations": feats["locations"], "change_files": feats["files"], "change_lines": feats["lines"],
        "category": category,
    }
    artifacts = ", ".join(f'{{ source = "{a}" }}' for a in cfg.artifacts)
    desc = {"bug-injection": f"Fix a regression injected into {cand.function_names} ({', '.join(cand.files)})",
            "multi-bug": f"Fix {len(cand.parts)} independent regressions in {cand.function_names}",
            "function-removal": f"Re-implement {cand.function_names} ({', '.join(cand.files)})"}[cand.strategy]
    toml = [
        'schema_version = "1.4"', f"artifacts = [{artifacts}]", "", "[task]",
        f'name = "coding-task-factory/{cand.id}"', 'version = "1.0.0"', f"description = {toml_str(desc)}",
        "authors = []", f'keywords = ["{cfg.language}", "{cfg.name}", "{category}", "generated"]', "",
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

def compose_groups(cfg: RepoConfig, singles: list[Candidate], bugs: int, texts: dict[str, str]):
    """Deterministically group validated single bugs: distinct functions,
    non-overlapping edits, preferring different files."""
    used: set[str] = set()
    for i, first in enumerate(singles):
        if first.id in used:
            continue
        group = [first]
        for prefer_new_file in (True, False):
            for other in singles[i + 1:]:
                if len(group) == bugs:
                    break
                if other.id in used or any(other.functions[0].name == g.functions[0].name and
                                           other.functions[0].file == g.functions[0].file for g in group):
                    continue
                if prefer_new_file and other.files[0] in {f for g in group for f in g.files}:
                    continue
                group.append(other)
        if len(group) < bugs:
            continue
        edits = [e for g in group for e in g.edits]
        try:
            apply_edits(texts, edits)
        except ValueError:  # overlapping edits (nested functions); skip this grouping
            continue
        used.update(g.id for g in group)
        fns = [g.functions[0] for g in group]
        cid = f"{cfg.name}-multi-" + "-".join(slug(f.name.split('.')[-1].split('::')[-1], 18) for f in fns) + \
              "-" + sha(*[g.id for g in group])[:6]
        desc = "; ".join(f"{g.functions[0].name}: {g.description}" for g in group)
        yield Candidate(cid, "multi-bug", edits, fns, desc,
                        injected=[x for g in group for x in g.injected], parts=group)


# ----------------------------------------------------------------------------
# Test-writing tasks (Python): "write a rigorous regression test"

TW_README = """Put your regression test in this directory as `test_regression.py` (pytest).

During grading the file is copied into `/app/tests/`, so the fixtures defined
in `tests/conftest.py` (for example `runner`) are available to it.
"""


def testwriting_instruction(cfg: RepoConfig, cand: Candidate, info: dict) -> str:
    fn = cand.functions[0]
    return (
        f"A defect has been introduced into `{fn.name}` in `{fn.file}` of the {cfg.project} library in `/app`. "
        "The project's tests that would have caught it have been removed. Your job is **not** to fix the "
        "defect, but to write a regression test that exposes it.\n\n"
        "Create `/app/regression/test_regression.py` (pytest) with one or more tests that:\n\n"
        "1. **fail** on the current code, because of the defect, and\n"
        f"2. **pass** once `{fn.name}` behaves correctly again.\n\n"
        "Grading runs your test file against the correct implementation, the current defective one, and "
        f"{info['wrong_count']} other plausible-but-wrong implementations of the same code that you cannot see. "
        "Your tests earn credit only if they pass on the correct implementation, fail on the defective one, "
        f"**and** fail on at least {int(info['min_rigor'] * 100)}% of the wrong implementations. Pin down the "
        "intended behaviour precisely; assertions about the source text rather than behaviour will not meet "
        "the bar. Do not modify the library source, which is ignored for grading.\n\n"
        "Your file is run from `/app/tests/` during grading, so the fixtures in `tests/conftest.py` (for "
        "example `runner`) are available. To try it locally: `cp /app/regression/test_regression.py "
        "/app/tests/ && cd /app && python -m pytest tests/test_regression.py`.\n"
    )


def package_testwriting(cfg: RepoConfig, cand: Candidate, f2p: list[str], info: dict, upstream: Path,
                        texts: dict[str, str], out_root: Path, seed: int) -> Path:
    fn = cand.functions[0]
    cid = f"{cfg.name}-test-{slug(fn.name)}-{sha(cand.id, 'test-writing')[:6]}"
    task = out_root / cid
    if task.exists():
        shutil.rmtree(task)
    shutil.copytree(FACTORY / "templates" / cfg.name / "environment", task / "environment")
    (task / "environment" / "vendor").mkdir()
    write_archive(cfg, upstream, {**info["edits"], "regression/README.md": TW_README},
                  task / "environment" / "vendor" / f"app-base.{cfg.archive_ext}")
    for extra in cfg.env_vendor:
        src = FACTORY / "vendor" / cfg.name / extra
        (shutil.copytree if src.is_dir() else shutil.copy2)(src, task / "environment" / "vendor" / extra)

    shutil.copytree(FACTORY / "templates" / f"{cfg.name}-testwriting" / "tests", task / "tests")
    write_variants(task / "tests" / "variants", info["variants"])
    (task / "tests" / "rigor.json").write_text(json.dumps({"min_rigor": info["min_rigor"]}) + "\n")
    (task / "tests" / "vendor").mkdir()
    shutil.copy2(FACTORY / "vendor" / cfg.name / f"app-upstream.{cfg.archive_ext}", task / "tests" / "vendor")
    for extra in cfg.tests_vendor:
        src = FACTORY / "vendor" / cfg.name / extra
        (shutil.copytree if src.is_dir() else shutil.copy2)(src, task / "tests" / "vendor" / extra)
    (task / "tests" / "test.sh").chmod(0o755)

    sol = task / "solution" / "files" / "regression" / "test_regression.py"
    sol.parent.mkdir(parents=True)
    sol.write_text(info["oracle"])
    (task / "solution" / "solve.sh").write_text(
        "#!/bin/bash\n# Reference solution: the upstream tests for this behaviour, as one regression file\n"
        f"# ({cfg.url} @ {cfg.commit}).\nset -euo pipefail\nmkdir -p /app/regression\n"
        "cp /solution/files/regression/test_regression.py /app/regression/test_regression.py\n")
    (task / "solution" / "solve.sh").chmod(0o755)
    (task / "instruction.md").write_text(testwriting_instruction(cfg, cand, info))
    diff = "".join("".join(difflib.unified_diff(texts.get(rel, (upstream / rel).read_text()).splitlines(keepends=True),
                                                 new.splitlines(keepends=True), f"a/{rel}", f"b/{rel}"))
                   for rel, new in sorted(info["edits"].items()))
    (task / "task_edit.diff").write_text(diff)

    signal = len(display_tests(f2p, limit=10 ** 6))
    score = 1 + (1 if signal <= 2 else 0) + (1 if info["wrong_count"] >= 5 else 0)
    level = "easy" if score <= 0 else "medium" if score <= 2 else "hard"
    why = (f"Static estimate (score {score}): infer intended behaviour of {fn.name} without its tests; "
           f"{info['wrong_count']} hidden wrong implementations to reject; the removed tests had {signal} case(s).")
    r = cfg.resources
    meta = {
        "generator": "test-writing", "seed": seed, "source_repo": cfg.url, "source_commit": cfg.commit,
        "language": cfg.language, "file": fn.file, "function": fn.name, "line": fn.line,
        "change": cand.description, "f2p_tests": len(f2p), "p2p_tests": 0,
        "removed_test_functions": info["removed_functions"], "wrong_implementations": info["wrong_count"],
        "oracle_rigor": info["oracle_rigor"], "min_rigor": info["min_rigor"],
        "adversarial_mutants": len(info["cheats"]), "adversarial_killed": sum(1 for v in info["cheats"].values() if v == 0),
        "partial_fixes_rejected": 0,
        "difficulty": level, "difficulty_score": score, "difficulty_explanation": why,
        "change_locations": 1, "change_files": 1, "change_lines": 1, "category": "test-writing",
    }
    toml = [
        'schema_version = "1.4"', 'artifacts = [{ source = "/app/regression" }]', "", "[task]",
        f'name = "coding-task-factory/{cid}"', 'version = "1.0.0"',
        f"description = {toml_str(f'Write a rigorous regression test exposing a defect in {fn.name}')}",
        "authors = []", f'keywords = ["{cfg.language}", "{cfg.name}", "test-writing", "generated"]', "",
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

def test_module_path(test_id: str) -> str:
    """'tests.test_utils.test_style::test_x[p]' -> 'tests/test_utils/test_style.py'."""
    return test_id.split("::", 1)[0].replace(".", "/") + ".py"


def test_function(test_id: str) -> str:
    return test_id.split("::", 1)[1].split("[", 1)[0]


def drop_functions(text: str, names: set[str]) -> str:
    """Module text without the given top-level test functions (decorators included)."""
    tree = ast.parse(text)
    lines = text.splitlines(keepends=True)
    spans = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
            start = min([node.lineno] + [d.lineno for d in node.decorator_list])
            spans.append((start, node.end_lineno))
    for start, end in sorted(spans, reverse=True):
        del lines[start - 1:end]
    out = "".join(lines)
    ast.parse(out)
    return out


def oracle_module(text: str, module: str, stable: set[str], all_ids: set[str]) -> str:
    """The upstream test module restricted to test functions whose every case passes reliably."""
    tree = ast.parse(text)
    keep_out = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
            ids = {t for t in all_ids if t.startswith(module + "::") and test_function(t) == node.name}
            if not ids or not ids <= stable:
                keep_out.add(node.name)
    return drop_functions(text, keep_out)


def testwriter_image(cfg: RepoConfig) -> str:
    template = FACTORY / "templates" / f"{cfg.name}-testwriting" / "tests"
    vendor = FACTORY / "vendor" / cfg.name
    files = sorted(p for p in template.rglob("*") if p.is_file())
    digest = sha(*(f"{p.relative_to(template)}:{hashlib.sha256(p.read_bytes()).hexdigest()}" for p in files),
                 *(hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(vendor.rglob("*")) if p.is_file()))
    tag = f"factory-testwriter-{cfg.name}:{digest[:12]}"
    if subprocess.run(["docker", "image", "inspect", tag], capture_output=True).returncode != 0:
        with tempfile.TemporaryDirectory() as ctx:
            ctx = Path(ctx)
            shutil.copytree(template, ctx, dirs_exist_ok=True)
            (ctx / "vendor").mkdir(exist_ok=True)
            shutil.copy2(vendor / f"app-upstream.{cfg.archive_ext}", ctx / "vendor")
            for extra in cfg.tests_vendor:
                src = vendor / extra
                (shutil.copytree if src.is_dir() else shutil.copy2)(src, ctx / "vendor" / extra)
            subprocess.run(["docker", "build", "-q", "-t", tag, str(ctx)], check=True, capture_output=True)
    return tag


def write_variants(root: Path, variants: dict[str, dict[str, str]]) -> None:
    for name, files in variants.items():
        (root / name).mkdir(parents=True, exist_ok=True)
        for rel, text in files.items():
            (root / name / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / name / rel).write_text(text)


def screen_tests(cfg: RepoConfig, image: str, variants: dict[str, dict[str, str]],
                 tests: dict[str, str]) -> dict:
    """Grade candidate test files against the variants in the test-writing verifier (cached)."""
    key = sha(image, json.dumps(variants, sort_keys=True), json.dumps(tests, sort_keys=True))
    cache = CACHE / cfg.name / "twruns" / f"{key}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        write_variants(tmp / "variants", variants)
        (tmp / "cands").mkdir()
        for name, text in tests.items():
            (tmp / "cands" / f"{name}.py").write_text(text)
        (tmp / "out").mkdir()
        subprocess.run(["docker", "run", "--rm", "--network", "none",
                        "-v", f"{tmp / 'variants'}:/tests/variants", "-v", f"{tmp / 'cands'}:/cands",
                        "-v", f"{tmp / 'out'}:/out", image, "python3", "/tests/run_variants.py",
                        "--tests-dir", "/cands", "--variants", "/tests/variants", "--config", "/tests/rigor.json",
                        "--out", "/out"], capture_output=True, timeout=1800)
        out_file = tmp / "out" / "screening.json"
        result = json.loads(out_file.read_text()) if out_file.exists() else {}
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(result))
    return result


def cheat_tests(cand: Candidate, texts: dict[str, str]) -> dict[str, str]:
    """Test files that must NOT earn reward: no assertion, always failing, and
    one that pins the source text around the defect instead of behaviour."""
    site, _ = cand.injected[0]
    text = texts[cand.files[0]]
    line_start = text.rfind("\n", 0, site.start) + 1
    line_end = text.find("\n", site.end)
    original_line = text[line_start:line_end].strip()
    rel = cand.files[0]
    return {
        "cheat_no_assertion": "def test_nothing():\n    pass\n",
        "cheat_always_fails": "def test_fails():\n    assert False\n",
        "cheat_source_peek": (
            "from pathlib import Path\n\n\ndef test_source_unchanged():\n"
            f"    src = (Path(__file__).resolve().parents[1] / {rel!r}).read_text()\n"
            f"    assert {original_line!r} in src\n"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True, choices=sorted(REPOS))
    ap.add_argument("--strategy", required=True, choices=sorted(SHORT))
    ap.add_argument("--count", type=int, default=5, help="tasks to produce")
    ap.add_argument("--bugs", type=int, default=2, help="defects per multi-bug task (2-3)")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--max-attempts", type=int, default=0, help="candidates to try (default 8x count)")
    ap.add_argument("--adversarial", type=int, default=6, help="sampled wrong fixes per task")
    ap.add_argument("--min-wrong-fixes", type=int, default=3)
    ap.add_argument("--min-kill-rate", type=float, default=0.75)
    ap.add_argument("--max-f2p-fraction", type=float, default=0.25)
    ap.add_argument("--min-rigor", type=float, default=0.75,
                    help="test-writing: share of hidden wrong implementations a test must reject")
    ap.add_argument("--workers", type=int, default=0)
    ap.add_argument("--out", type=Path, default=ROOT / "tasks" / "generated")
    args = ap.parse_args()

    cfg = REPOS[args.repo]
    started = time.time()
    # multi-bug draws its single bugs from its own seeded stream, so its defects
    # differ from the ones used by bug-injection tasks with the same seed
    rng_key = f"{cfg.name}:{args.strategy}:{args.seed}"
    if args.strategy == "multi-bug" and args.bugs != 2:
        rng_key += f":bugs{args.bugs}"  # its own pool, so tasks don't reuse the 2-bug tasks' defects
    rng = random.Random(rng_key)
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
    log(f"[..] {len(files)} source files, {len(fns)} functions, {sum(len(f.sites) for f in fns)} mutation sites, "
        f"{sum(len(f.deletions) for f in fns)} deletion sites")
    adv_seed = f"{cfg.name}:{args.strategy}:{args.seed}:adversarial"

    def evaluate(cand: Candidate, index: int) -> dict:
        rec = {"index": index, "id": cand.id, "file": ", ".join(cand.files), "function": cand.function_names,
               "line": cand.functions[0].line, "change": cand.description}
        new_files = apply_edits(texts, cand.edits)
        results = run_tests(cfg, image, upstream, new_files, edits_key("cand", new_files), run_timeout)
        if "__timeout__" in results:
            return {**rec, "status": "rejected", "reason": "hangs"}
        if not results:
            return {**rec, "status": "rejected", "reason": "build-failure"}
        now = passed(results)
        f2p, p2p = sorted(stable - now), sorted(stable & now)
        rec.update(f2p=len(f2p), p2p=len(p2p))
        if not f2p:
            return {**rec, "status": "rejected", "reason": "undetected"}
        if len(f2p) > args.max_f2p_fraction * len(stable):
            return {**rec, "status": "rejected", "reason": "too-broad"}
        must, sampled = wrong_fixes(cfg, cand, texts, random.Random(f"{adv_seed}:{cand.id}"), args.adversarial)
        if len(must) + len(sampled) < args.min_wrong_fixes:
            return {**rec, "status": "rejected", "reason": "too-few-wrong-fixes"}
        partial_killed, killed, survivors = 0, 0, []
        for desc, files_ in must:
            res = run_tests(cfg, image, upstream, files_, edits_key("adv", files_), run_timeout)
            if grade(res, f2p, p2p) == 0:
                partial_killed += 1
            else:
                survivors.append(desc)
        for desc, files_ in sampled:
            res = run_tests(cfg, image, upstream, files_, edits_key("adv", files_), run_timeout)
            if grade(res, f2p, p2p) == 0:
                killed += 1
            else:
                survivors.append(desc)
        total = len(must) + len(sampled)
        rate = (killed + partial_killed) / total
        adv = {"mutants": total, "killed": killed + partial_killed, "kill_rate": round(rate, 3),
               "partial_fixes": len(must), "partial_killed": partial_killed, "survivors": survivors}
        if cand.parts:
            adv["defects"] = defect_tests(cand, f2p)
        rec.update(adversarial=adv)
        if partial_killed < len(must):
            return {**rec, "status": "rejected", "reason": "masked-bugs"}
        if rate < args.min_kill_rate:
            return {**rec, "status": "rejected", "reason": "weak-tests"}
        rec["_payload"] = (cand, f2p, p2p, adv)
        return {**rec, "status": "accepted"}

    def defect_tests(cand: Candidate, f2p: list[str]) -> list[dict]:
        """Tests each defect breaks on its own (exclusive ones when it has any)."""
        per = []
        for part in cand.parts:
            pf = apply_edits(texts, part.edits)
            res = run_tests(cfg, image, upstream, pf, edits_key("cand", pf), run_timeout)
            per.append(set(stable - passed(res)) & set(f2p))
        out = []
        for i, part in enumerate(cand.parts):
            others = set().union(*(per[j] for j in range(len(per)) if j != i))
            own = per[i] - others
            out.append({"function": part.functions[0].name, "file": part.files[0], "change": part.description,
                        "tests": sorted(own or per[i])})
        return out

    def run_stage(candidates, target: int, max_attempts: int, label: str) -> tuple[list, list, int]:
        """Evaluate candidates in parallel until `target` are accepted; returns
        (accepted payloads in enumeration order, records, attempts)."""
        records, accepted = [], []
        attempts = 0
        with cf.ThreadPoolExecutor(max_workers=workers) as pool:
            pending: dict[cf.Future, Candidate] = {}
            exhausted = False
            while True:
                while not exhausted and len(pending) < workers and attempts < max_attempts \
                        and len(accepted) < target:
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
                    log(f"[{'OK' if rec['status'] == 'accepted' else '--'}] ({label}) {rec['id']:<62} {rec['status']}"
                        f"{' (' + rec.get('reason', '') + ')' if rec.get('reason') else ''}{extra}")
        # first `target` accepted in enumeration order: independent of thread timing
        accepted.sort(key=lambda t: t[0])
        keep = {idx for idx, _ in accepted[:target]}
        for rec in records:
            rec.pop("_payload", None)
            if rec["status"] == "accepted" and rec["index"] not in keep:
                rec.update(status="surplus", reason="target count already reached")
        return [p for idx, p in accepted if idx in keep], sorted(records, key=lambda r: r["index"]), attempts

    singles_stage = None
    if args.strategy == "test-writing":
        if cfg.language != "python":
            log("[FAIL] test-writing tasks are implemented for Python repositories (click) only")
            return 1
        tw_image = testwriter_image(cfg)
        pool_target = args.count * 3
        pool, pool_records, pool_attempts = run_stage(
            enumerate_candidates(cfg, "bug-injection", fns, texts, rng), pool_target,
            args.max_attempts or pool_target * 8, "single")
        singles_stage = {"candidates_tried": pool_attempts, "validated_bugs": len(pool),
                         "funnel": funnel(pool_records)}
        log(f"[..] {len(pool)} validated single bugs for test-writing tasks")
        all_ids = set(ref1) | set(ref2)
        accepted_tw, records, attempts = [], [], 0
        for cand, f2p, _p2p, adv in pool:
            if len(accepted_tw) >= args.count:
                break
            attempts += 1
            rec = {"index": attempts, "id": cand.id, "file": cand.files[0], "function": cand.function_names,
                   "change": cand.description, "f2p": len(f2p)}
            modules: dict[str, set[str]] = {}
            for t in f2p:
                if "::" in t and (upstream / test_module_path(t)).exists():
                    modules.setdefault(test_module_path(t), set()).add(test_function(t))
            top = sorted(m for m in modules if len(Path(m).parts) == 2)
            if not top:
                records.append({**rec, "status": "rejected", "reason": "oracle-unavailable"})
                log(f"[--] (test) {cand.id:<62} rejected (oracle-unavailable)")
                continue
            best = max(top, key=lambda m: len(modules[m]))
            oracle = oracle_module((upstream / best).read_text(), best[:-3].replace("/", "."), stable, all_ids)
            edits = {cand.files[0]: apply_edits(texts, cand.edits)[cand.files[0]]}
            for m, names in modules.items():
                edits[m] = drop_functions((upstream / m).read_text(), names)
            _, sampled = wrong_fixes(cfg, cand, texts, random.Random(f"{adv_seed}:{cand.id}"), args.adversarial)
            killed = [(d, f) for d, f in sampled if d not in adv.get("survivors", [])]
            if len(killed) < args.min_wrong_fixes:
                records.append({**rec, "status": "rejected", "reason": "too-few-wrong-fixes"})
                log(f"[--] (test) {cand.id:<62} rejected (too-few-wrong-fixes)")
                continue
            variants = {"reference": {}, "buggy": {cand.files[0]: edits[cand.files[0]]}}
            for i, (_d, files_) in enumerate(killed, 1):
                variants[f"wrong_{i}"] = files_
            cheats = cheat_tests(cand, texts)
            result = screen_tests(cfg, tw_image, variants, {"oracle": oracle, **cheats})
            o = result.get("oracle", {})
            cheat_rewards = {k: result.get(k, {}).get("reward") for k in cheats}
            rec.update(oracle=o, cheats=cheat_rewards, wrong_implementations=len(killed))
            if o.get("reward") != 1:
                reason = "oracle-not-rigorous" if o.get("valid") and o.get("detects_bug") else "oracle-invalid"
                records.append({**rec, "status": "rejected", "reason": reason})
                log(f"[--] (test) {cand.id:<62} rejected ({reason}) rigor={o.get('rigor')}")
                continue
            if any(v != 0 for v in cheat_rewards.values()):
                records.append({**rec, "status": "rejected", "reason": "cheat-test-passes"})
                log(f"[--] (test) {cand.id:<62} rejected (cheat-test-passes) {cheat_rewards}")
                continue
            info = {"edits": edits, "variants": variants, "oracle": oracle, "cheats": cheat_rewards,
                    "wrong_count": len(killed), "oracle_rigor": o.get("rigor"), "min_rigor": args.min_rigor,
                    "removed_functions": sum(len(v) for v in modules.values())}
            accepted_tw.append((cand, f2p, info))
            records.append({**rec, "status": "accepted"})
            log(f"[OK] (test) {cand.id:<62} accepted oracle_rigor={o.get('rigor')} cheats={cheat_rewards}")
        out_root = args.out / cfg.name
        out_root.mkdir(parents=True, exist_ok=True)
        for cand, f2p, info in accepted_tw:
            package_testwriting(cfg, cand, f2p, info, upstream, texts, out_root, args.seed)
        report = {"repo": cfg.name, "strategy": args.strategy, "seed": args.seed, "count_requested": args.count,
                  "candidates_tried": attempts, "accepted": len(accepted_tw), "funnel": funnel(records),
                  "reference": {"tests": len(ref1), "stable_passing": len(stable), "flaky": len(flaky)},
                  "thresholds": {"min_rigor": args.min_rigor, "min_wrong_fixes": args.min_wrong_fixes},
                  "single_bug_stage": singles_stage, "elapsed_sec": round(time.time() - started, 1),
                  "candidates": records}
        report_path = out_root / f"report-test-seed{args.seed}.json"
        report_path.write_text(json.dumps(report, indent=2) + "\n")
        log(f"[OK] {len(accepted_tw)}/{args.count} tasks from {attempts} candidates in {report['elapsed_sec']}s; "
            f"funnel {report['funnel']}; report {report_path.relative_to(ROOT)}")
        return 0 if len(accepted_tw) == args.count else 2
    if args.strategy == "multi-bug":
        # stage 1: a pool of individually validated single bugs
        pool_target = args.count * args.bugs + args.bugs
        singles_iter = enumerate_candidates(cfg, "bug-injection", fns, texts, rng)
        pool, pool_records, pool_attempts = run_stage(singles_iter, pool_target,
                                                      args.max_attempts or pool_target * 8, "single")
        singles = [p[0] for p in pool]
        singles_stage = {"candidates_tried": pool_attempts, "validated_bugs": len(singles),
                         "funnel": funnel(pool_records)}
        log(f"[..] {len(singles)} validated single bugs for composition")
        accepted, records, attempts = run_stage(compose_groups(cfg, singles, args.bugs, texts), args.count,
                                                10 ** 6, "multi")
    else:
        accepted, records, attempts = run_stage(enumerate_candidates(cfg, args.strategy, fns, texts, rng),
                                                args.count, args.max_attempts or args.count * 8, "task")

    out_root = args.out / cfg.name
    out_root.mkdir(parents=True, exist_ok=True)
    for cand, f2p, p2p, adv in accepted:
        package(cfg, cand, f2p, p2p, adv, upstream, texts, out_root, args.seed)

    report = {
        "repo": cfg.name, "strategy": args.strategy, "seed": args.seed, "count_requested": args.count,
        "candidates_tried": attempts, "accepted": len(accepted), "funnel": funnel(records),
        "reference": {"tests": len(ref1), "stable_passing": len(stable), "flaky": len(flaky)},
        "thresholds": {"min_kill_rate": args.min_kill_rate, "max_f2p_fraction": args.max_f2p_fraction,
                       "adversarial_per_task": args.adversarial, "min_wrong_fixes": args.min_wrong_fixes},
        "tasks": [c.id for c, *_ in accepted],
        "elapsed_sec": round(time.time() - started, 1),
        "candidates": records,
    }
    if singles_stage:
        report["bugs_per_task"] = args.bugs
        report["single_bug_stage"] = singles_stage
    suffix = f"{SHORT[args.strategy]}{args.bugs if args.strategy == 'multi-bug' else ''}"
    report_path = out_root / f"report-{suffix}-seed{args.seed}.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    log(f"[OK] {len(accepted)}/{args.count} tasks from {attempts} candidates in {report['elapsed_sec']}s; "
        f"funnel {report['funnel']}; report {report_path.relative_to(ROOT)}")
    return 0 if len(accepted) == args.count else 2


def funnel(records: list[dict]) -> dict[str, int]:
    out: dict[str, int] = {}
    for rec in records:
        key = rec["status"] if rec["status"] != "rejected" else f"rejected:{rec['reason']}"
        out[key] = out.get(key, 0) + 1
    return dict(sorted(out.items()))


if __name__ == "__main__":
    sys.exit(main())
