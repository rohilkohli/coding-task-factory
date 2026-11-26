"""Per-repository settings for the task generator."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RepoConfig:
    name: str
    project: str  # human-readable project name for instructions
    language: str  # python | typescript | cpp
    url: str
    commit: str
    archive_ext: str  # tar.gz | tar.br (format of app-*.tar.* archives)
    artifacts: tuple[str, ...]  # container paths the verifier receives
    source_globs: tuple[str, ...]  # files the generator may modify (relative to /app)
    source_exclude: tuple[str, ...] = ()
    env_vendor: tuple[str, ...] = ()  # extra files from factory/vendor/<repo> for environment/vendor
    tests_vendor: tuple[str, ...] = ()  # extra files from factory/vendor/<repo> for tests/vendor
    test_hint: str = ""
    workers: int = 4  # concurrent verifier runs
    resources: dict = field(default_factory=dict)


REPOS: dict[str, RepoConfig] = {
    "click": RepoConfig(
        name="click", project="click", language="python",
        url="https://github.com/pallets/click", commit="08b803cf32ceb2ae6a772c62d5da42757a897d44",
        archive_ext="tar.gz", artifacts=("/app/src",),
        source_globs=("src/click/*.py",),
        source_exclude=("src/click/_winconsole.py", "src/click/_compat.py", "src/click/__init__.py",
                        "src/click/globals.py"),
        env_vendor=("wheels",), tests_vendor=("wheels",),
        test_hint="Run the test suite from `/app` with `python -m pytest tests`.",
        workers=4, resources={"cpus": 1, "memory_mb": 2048, "verifier_timeout": 300},
    ),
    "zod": RepoConfig(
        name="zod", project="Zod", language="typescript",
        url="https://github.com/colinhacks/zod", commit="d40c329910436e528d3c26cb1b9179e05abebf05",
        archive_ext="tar.br", artifacts=("/app/packages/zod/src",),
        source_globs=("packages/zod/src/v4/core/*.ts", "packages/zod/src/v4/classic/*.ts",
                      "packages/zod/src/v4/mini/*.ts"),
        source_exclude=("packages/zod/src/v4/core/versions.ts",),
        env_vendor=("node_modules.tar.br",), tests_vendor=("node_modules.tar.br",),
        test_hint="Run the test suite from `/app` with `npx vitest run --project zod`.",
        workers=2, resources={"cpus": 2, "memory_mb": 4096, "verifier_timeout": 900},
    ),
    "jsoncpp": RepoConfig(
        name="jsoncpp", project="JsonCpp", language="cpp",
        url="https://github.com/open-source-parsers/jsoncpp", commit="93acc7b155048f1a66c43235cc205519f1e7a6ea",
        archive_ext="tar.gz", artifacts=("/app/src/lib_json", "/app/include"),
        source_globs=("src/lib_json/*.cpp",),
        test_hint=(
            "CMake is not installed; build and run the unit tests with:\n\n"
            "```bash\nmkdir -p /tmp/b && g++ -std=c++17 -O1 -Iinclude -Isrc/test_lib_json src/lib_json/*.cpp "
            "src/test_lib_json/{main,jsontest,fuzz}.cpp -o /tmp/b/jsoncpp_test && /tmp/b/jsoncpp_test\n```\n\n"
            "Data-driven tests: build `src/jsontestrunner/main.cpp` with the library as `/tmp/b/jsontestrunner` "
            "and run `python3 test/runjsontests.py /tmp/b/jsontestrunner test/data`."
        ),
        workers=3, resources={"cpus": 2, "memory_mb": 4096, "verifier_timeout": 900},
    ),
}
