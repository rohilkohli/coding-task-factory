# Coding Task Factory: Research Brief

**Purpose:** set the design of our Innodata AI Hackathon (Challenge 01) entry from published evidence. The entry generates Harbor-format coding tasks from `pallets/click`, `colinhacks/zod` and `open-source-parsers/jsoncpp`.
**Type:** rapid scoping review, not a full systematic review.
**Search date:** 2026-11-26.
**Method:** K-Dense *Scientific Agent Skills* (`literature-review` for method, `paper-lookup` for retrieval). Raw responses and query logs are in `sources/`.

---

## 1. Bottom line

1. **Don't build tasks from these repos' old pull requests.** click, zod and jsoncpp are popular and old, so models have likely memorized their history. On SWE-bench Verified, models found the buggy file from the issue text alone 76% of the time, against at most 53% on repos outside the benchmark [36]. A second study found models 3× better overall and 6× better at finding the edited files on SWE-bench Verified than on comparable benchmarks [37]. Over 94% of SWE-bench issues predate model training cutoffs [26].
2. **Use three task generators the literature has validated:**
   - **Test-traced feature removal** [22, 40]: remove a working feature and keep the original code as the reference. This is the most reliable option.
   - **LLM-designed new features** [15]: the hackathon's "discount codes" example. This is the most novel option.
   - **Bug injection** [14, 16]: the cheapest way to get variety.
3. **Treat validation as the product.** Published benchmarks score agents too high, mostly because their tests are weak:
   - 31% of passing SWE-bench patches had inadequate tests [26].
   - 1 in 5 "solved" patches from top agents was semantically wrong [29].
   - 29.6% of plausible patches behaved differently from the ground truth [28].

   An **adversarial wrong-patch check** (every task must reject deliberately wrong solutions) [29, 34] is our clearest differentiator. Accuracy and validation is 25% of the score.
4. **Calibrate difficulty against real solvers** [19]. The strongest results come from benchmarks that report a wide spread of pass rates. Example: a state-of-the-art model scored 74.4% on SWE-bench but only 11.0% on FeatureBench [22].

---

## 2. Methods

| Item | Detail |
|---|---|
| Question | How do existing systems create, validate and diversify repository-level coding tasks for evaluating AI agents, and what failure modes have been documented? |
| Sources | **OpenAlex** (primary; indexes arXiv, ACL, ACM, NeurIPS), 12 queries with a filter for publications from 2023 onward, top 50 by relevance each. **arXiv API**: 11 queries, of which 4 returned results; the other 7 were throttled or got HTTP 503. **Semantic Scholar**: HTTP 429 on all 5 queries, since there is no API key. **OpenAlex title search**: 5 gap queries. |
| Records | 487 unique records from OpenAlex. |
| Screening | Title screen for relevance to repo-level task construction, validation, contamination, feature tasks or harness design. **40 papers included**: 39 from the main search plus SWE-Flow from gap search. |
| Extraction | From abstracts only (no full text). Every number below is as the authors report it in the abstract. |
| Provenance | `sources/openalex/_provenance.log`, `sources/arxiv/_provenance.log`, `sources/s2/_provenance.log`, `sources/included_final.json` |

**Limitations** (per the `scientific-critical-thinking` checklist):
- **Not exhaustive:** coverage is the top 50 results per query, with no full-text screening.
- **Mostly unreviewed:** many included papers are 2025–26 arXiv preprints, and their numbers are self-reported.
- **Missing papers:** R2E-Gym and SWE-PolyBench were not retrieved; arXiv and Semantic Scholar were unavailable from this network.
- **No independent study of Harbor:** no Harbor paper exists in these indexes. Harbor's design comes from the maintainers' docs and its predecessor, Terminal-Bench [39].

---

## 3. Findings by theme

### 3.1 Where tasks come from

| Strategy | Representative work | How it works | Strength | Weakness for *our* repos |
|---|---|---|---|---|
| **Mine merged PRs/issues** | SWE-bench [1], SWE-Gym [2], SWE-rebench [3,4], SWE-bench-Live [5], Multi-SWE-bench [6], SWE-Bench++ [8], SWE-Next [10], SWE-Factory [11], SWE-Universe [9] | Base commit + PR fix; keep tests that fail before and pass after ("fail-to-pass", F2P) | Realistic, human-written reference | **Contamination** [36,37]; limited supply in 3 repos; solution leakage in issue text (32.67% of "solves" were leaks [26]) |
| **Test-traced feature removal** | FeatureBench [22], SWE-Flow [40], FEA-Bench [21] | Trace from unit tests along a dependency graph, remove the feature's code, keep the rest passing | Reference = real upstream code; tests already exist; hard (best model 11.0% [22]) | Original code may be memorized (5-gram overlap up to 35% on SWE-bench [36]) |
| **Synthetic bug injection** | SWE-smith [14], Self-play SWE-RL [16] | Mutate code so existing tests break; the bug is specified by a test patch | Cheap; 100s–1,000s per repo [14]; no human labels | Bugs can be artificial; must rewrite the task as a realistic report |
| **LLM-designed new feature** | SWE-Playground [15], benchmark-generation graphs [20], TermiGen [18] | LLM writes spec, implementation and tests, refined in a multi-agent loop until the task runs [18] | Novel, so contamination-free; matches the hackathon example | Highest risk of wrong reference or weak tests; needs the strongest checks |
| **Long-horizon / non-bugfix** | SWE-EVO [24], SWE Atlas [25], SWE-Bench Pro [7] | Release notes, refactoring, test-writing, Q&A | Breadth of task types | Expensive to verify; SWE Atlas needs rubric grading |

### 3.2 Building environments
- **Agent-built environments:** Repo2Run builds Dockerfiles with an agent until the tests run, succeeding 86% of the time [12]. SWE-Builder costs about $0.047 per valid instance [11].
- **Reusing environments:** SWE-Next reuses one environment across nearby commits and kept storage to 639 GB for 3,971 repos [10].
- **Agents are weak at setup:** they succeed on only 38.9–57.4% of repo-setup tasks [13]. So we **pre-build** each environment and don't make setup part of the task.
- **For us:** with 3 fixed repos, one hand-verified, digest-pinned image per repo is enough. Agent-built environments aren't needed.

### 3.3 Validation: what goes wrong and the fixes

| Failure mode | Evidence | Fix in the literature |
|---|---|---|
| Weak tests accept wrong patches | 31.08% of passing patches suspicious [26]; 345 wrong patches marked as passing [27]; 1 in 5 top-agent "solves" wrong, top score falls from 78.8% to 62.2% [29]; 29.6% behave differently from ground truth [28] | Coverage-guided test augmentation [27,29]; synthesized test cases for patch evaluation [23]; **mutation-driven adversarial wrong patches** [29]; differential patch testing (PatchDiff) [28]; mutation-guided test generation with LLM equivalent-mutant detection [34] |
| Flaky or unparseable test results | Manual log parsing was a bottleneck [11] | **Exit-code-based** F2P check, F1 0.99 against manual inspection [11] |
| Fix breaks other code | — | Keep only "strict test improvements without regressions" (pass-to-pass, P2P) [10] |
| Solution leaked in the task text | 32.67% of "solves" [26] | Strip hints from the instruction; LLM-judge leak check |
| Unclear spec, or tests stricter than the spec | Flagged as common confounders [4]; agents can't tell well-specified from underspecified tasks [35]; gold solutions or hidden evaluation info leaked [33] | Ensemble of LLM judges, validated against human labels [4]; automated labels for issue clarity, test coverage and effort at $5.10 per 1,000 vs about $100k by hand [32]; minimal task refinement [33] |
| Agent tampers with or overfits the tests | Test overfitting [31]; leakage channels [33] | Hidden tests, separate verifier, sandbox (Harbor's defaults) |
| Unrealistic prompts inflate scores | Formal issue text overestimates performance by >50% vs realistic user queries [30] | Write instructions in the style of real users and developers |

### 3.4 Contamination and freshness
- **Static benchmarks inflate scores:** SWE-rebench's fresh tasks show inflated SWE-bench Verified scores for some models [3]. SWE-bench-Live shows a large gap against static benchmarks [5]. LiveBench keeps itself fresh with monthly updates [38]. SWE-Bench Pro keeps held-out and commercial sets private [7].
- **Diagnostic probes:** name the file to edit from the task text alone [36,37], and measure verbatim n-gram overlap with the original code [36]. Both are cheap enough for us to run on every task.

### 3.5 Variety and difficulty
- **Controlled variety:** SkillSynth controls variety explicitly by sampling paths through a skill graph [17]. Counting tasks alone isn't enough.
- **Calibrated difficulty:** CalibForge keeps tasks that sit in a "learnable zone" between solvers. One approach targets disagreement across a pool of solvers; the other keeps tasks a strong solver passes and a weak solver fails [19].
- **Spread across languages:** language spread is standard in recent pipelines, from 7 languages [6] up to 11 [8] and 20 [4].

### 3.6 Harness
- **Harbor's lineage:** Harbor comes from the Terminal-Bench team. Terminal-Bench 2.0 has 89 hand-curated tasks, each with a unique environment, a human-written solution and comprehensive tests, and frontier agents score below 65% [39].
- **Our gap:** Harbor gives us the task format, the `oracle` and `nop` agents, and sandboxing. The literature shows that what's missing is **automated, scalable task quality**, and that's where our system adds value.

---

## 4. Design decisions this evidence supports

### 4.1 Three generators, chosen per repo

| Generator | Evidence | Reference solution | Hidden tests |
|---|---|---|---|
| **G1 Feature removal** (test-traced) | [22, 40] | Original upstream code (known correct) | Upstream tests for the feature, plus generated tests |
| **G2 New feature** (LLM-designed; the hackathon's example) | [15, 18, 20] | LLM-written, then validated | LLM-written, then hardened |
| **G3 Bug injection** (rewritten as a realistic bug report) | [14, 16, 30] | Revert the injected change | Existing tests that the bug breaks |

### 4.2 Validation checks (every task must pass all of them)

| # | Check | Pass condition | Evidence |
|---|---|---|---|
| V1 | Reproducible build | Pinned image digest; build succeeds twice | [11, 12] |
| V2 | Tests fail on base | Harbor `nop` agent → reward 0 (exit-code based) | [11] |
| V3 | Oracle passes, ×3 | Harbor `oracle` agent → reward 1 on 3 of 3 runs | [10] |
| V4 | No regressions | Full upstream suite still passes with the reference (P2P) | [10] |
| V5 | **Adversarial wrong patches** | Mutants of the reference and near-miss LLM patches must all fail; report a kill score per task | [28, 29, 34] |
| V6 | Spec quality | LLM-judge ensemble: clarity, test–spec alignment, no solution leakage | [4, 26, 32, 33, 35] |
| V7 | Anti-tampering | Separate verifier, tests hidden from the agent, network off | [31, 33], Harbor docs |
| V8 | Difficulty calibration | Run a weak and a strong agent; label difficulty; drop tasks everything solves or nothing solves | [19, 22] |
| V9 | Contamination probe | File-localization from instruction alone; n-gram overlap with upstream code (G1) | [36, 37] |

### 4.3 Evidence for the "different, reliable, repeatable" requirement
- **Different:** a coverage matrix of repo (3) × generator (3) × module × difficulty, sampling over a module graph [17], and near-duplicate removal on task instructions.
- **Reliable:** per-task results for V1–V9, an overall acceptance funnel ("N generated → M accepted"), and mutation kill scores.
- **Repeatable:** seeded generation, pinned commits and image digests, and a re-run that produces identical task directories (hash-compared).

### 4.4 How this maps to the judging criteria

| Criterion (weight) | What we show |
|---|---|
| Working implementation (25%) | End-to-end Harbor runs: `oracle`, `nop`, plus real agents |
| Accuracy & validation (25%) | Checks V1–V9; adversarial kill scores; acceptance funnel |
| Meaningful variation (20%) | 3 languages × 3 generators × modules × difficulty spread |
| Originality & engineering (15%) | Adversarial-patch and contamination checks, which are rare even in published pipelines |
| Practical impact & clarity (15%) | Reusable CLI, dashboard, the numbers from this brief |

---

## 5. Applied to the three required repos (probed 2026-11-26)

| Repo | Language / test tool | Test surface (counted) | Best-fit generators | Notes |
|---|---|---|---|---|
| **click** | Python ≥3.11 / pytest | 21 test files, 565 `test_` functions, 17 modules (`core`, `types`, `parser`, `shell_completion`, `termui`, `testing`, ...) | G1 (e.g. parameter types, shell completion), G2 (new param type or option behaviour), G3 | Easiest to start with; fast tests |
| **zod** (v4) | TypeScript / vitest | 138 test files, about 2,190 `test()`/`it()` calls; per-feature files (`iban`, `credit-card`, `codec`, `to-json-schema`, locales, ...) | G1 (string formats, codecs, JSON Schema export), G2 (new format validator or locale) | Repo declares `packageManager: nub@0.8.3` (unusual), so the Docker build must be verified first |
| **jsoncpp** | C++ / CMake + custom runner | 135 unit fixtures + 69 data-driven `.json` cases | G1 (reader/writer settings, e.g. comments, special floats), G3 (parser bugs) | Data-driven input/expected pairs make strong hidden tests; compile time affects runtime budgets |

---

## 6. Open risks
1. **G1 memorization:** agents may reproduce upstream code from memory. V9 measures this, and the report should state it openly rather than hide it.
2. **G2 reference correctness:** an LLM-written reference can be wrong in ways its own tests share. V5 and V6 reduce this but can't eliminate it, so spot-check a sample by hand.
3. **LLM-judge bias in V6:** LLM judges have documented biases (see LiveBench's critique of judges [38]). Use them as filters, not as the final score; the final score stays execution-based.
4. **Time:** with 10 days left, ship G1 and G3 first, since they're the most reliable, then add G2.

---

## 7. References

Retrieved via OpenAlex on 2026-11-26. Citation counts are OpenAlex counts at access time. Claims above are from each paper's abstract.

1. Jimenez, Carlos E., Yang, John, Alexander Wettig et al. (2024). *SWE-bench: Can Language Models Resolve Real-World GitHub Issues?*. International Conference on Learning Representations. https://doi.org/10.48550/arxiv.2310.06770
2. Jiayi Pan, Xingyao Wang, Graham Neubig et al. (2025). *Training Software Engineering Agents and Verifiers with SWE-Gym*. International Conference on Machine Learning. https://doi.org/10.48550/arxiv.2412.21139
3. Ibragim Badertdinov, Alexander Golubev, Maksim Nekrashevich et al. (2025). *SWE-rebench: An Automated Pipeline for Task Collection and Decontaminated Evaluation of Software Engineering Agents*. neural information processing systems. https://doi.org/10.52202/085713-0788
4. Ibragim Badertdinov, Maksim Nekrashevich, Anton Shevtsov et al. (2026). *SWE-rebench V2: Language-Agnostic SWE Task Collection at Scale*. International Conference on Machine Learning. https://doi.org/10.48550/arxiv.2602.23866
5. Linghao Zhang, Shilin He, Chaoyun Zhang et al. (2025). *SWE-bench Goes Live!*. neural information processing systems. https://doi.org/10.52202/085713-4923
6. Daoguang Zan, Zhirong Huang, Wei Liu et al. (2025). *Multi-SWE-bench: A Multilingual Benchmark for Issue Resolving*. neural information processing systems. https://doi.org/10.52202/085713-2111
7. Xiang Bo Deng, Jeff Da, Edwin Pan et al. (2026). *SWE-Bench Pro: Can AI Agents Solve Long-Horizon Software Engineering Tasks?*. International Conference on Machine Learning. https://doi.org/10.48550/arxiv.2509.16941
8. Lilin Wang, Lucas Ramalho, Alan Celestino et al. (2025). *SWE-Bench++: A Framework for the Scalable Generation of Software Engineering Benchmarks from Open-Source Repositories*. arXiv. https://doi.org/10.48550/arxiv.2512.17419
9. Mouxiang Chen, Lei Zhang (张磊), Yunlong Feng et al. (2026). *SWE-Universe: Scale Real-World Verifiable Environments to Millions*. arXiv. https://doi.org/10.48550/arxiv.2602.02361
10. Jiarong Liang, Zhiheng Lyu, Zijie Liu et al. (2026). *SWE-Next: Scalable Real-World Software Engineering Tasks for Agents*. arXiv. https://doi.org/10.48550/arxiv.2603.20691
11. Lianghong Guo, Yanlin Wang, C B Li et al. (2026). *SWE Data Construction, Automatically!*. Proceedings of the ACM on software engineering.. https://doi.org/10.1145/3797119
12. Ruida Hu, Chao Peng, Xinchen Wang et al. (2025). *Repo2Run: Automated Building Executable Environment for Code Repository at Scale*. neural information processing systems. https://doi.org/10.52202/085713-1096
13. Arora, Avi, Jinu Jang, Roshanak Zilouchian Moghaddam et al. (2025). *SetupBench: Assessing Software Engineering Agents' Ability to Bootstrap Development Environments*. arXiv. https://doi.org/10.48550/arxiv.2507.09063
14. John Yang, K. Lieret, Carlos Jimenez et al. (2025). *SWE-smith: Scaling Data for Software Engineering Agents*. neural information processing systems. https://doi.org/10.52202/085713-3239
15. Yiqi Zhu, Akshat Gandhi, Graham Neubig et al. (2025). *Training Versatile Coding Agents in Synthetic Environments*. arXiv. https://doi.org/10.48550/arxiv.2512.12216
16. Yuxiang Wei, Zhiqing Sun, Emily McMilin et al. (2026). *Toward Training Superintelligent Software Agents through Self-Play SWE-RL*. International Conference on Machine Learning. https://doi.org/10.48550/arxiv.2512.18552
17. Zhiyuan Fan, TingHao Yu, Yuanjun Cai et al. (2026). *Toward Scalable Terminal Task Synthesis via Skill Graphs*. arXiv. https://doi.org/10.48550/arxiv.2604.25727
18. Kaijie Zhu, Yuzhou Nie, Yijiang Li et al. (2026). *TermiGen: High-Fidelity Environment and Robust Trajectory Synthesis for Terminal Agents*. arXiv. https://doi.org/10.48550/arxiv.2602.07274
19. Fanzhe Meng, Guoxin Chen, Jiale Zhao et al. (2026). *CalibForge: Adversarial Solver Calibration for Scaling Learnable Terminal Tasks*. arXiv. https://doi.org/10.48550/arxiv.2608.06352
20. Eitan Farchi, Shmulik Froimovich, Rami Katan et al. (2024). *Automatic Generation of Benchmarks and Reliable LLM Judgment for Code Tasks*. arXiv. https://doi.org/10.48550/arxiv.2410.21071
21. Wei Li, Xin Zhang, Zhongxin Guo et al. (2025). *FEA-Bench: A Benchmark for Evaluating Repository-Level Code Generation for Feature Implementation*. Proceedings of the conference - Association for Computational Linguistics. Meeting. https://doi.org/10.18653/v1/2025.acl-long.839
22. Qixing Zhou, Jiacheng Zhang, Haiyang Wang et al. (2026). *FeatureBench: Benchmarking Agentic Coding for Complex Feature Development*. International Conference on Learning Representations. https://doi.org/10.48550/arxiv.2602.10975
23. Haoran Wang, Zhenyu Hou, Yao Wei et al. (2025). *SWE-Dev: Building Software Engineering Agents with Training and Inference Scaling*. Findings of the Association for Computational Linguistics: ACL (Findings of ACL). https://doi.org/10.18653/v1/2025.findings-acl.193
24. Tue Le, Minh V. T. Thai, Dung Nguyen Manh et al. (2025). *SWE-EVO: Benchmarking Coding Agents in Long-Horizon Software Evolution Scenarios*. arXiv. https://doi.org/10.48550/arxiv.2512.18470
25. Mohit Raghavendra, Soham Dan, Miguel Romero Calvo et al. (2026). *SWE Atlas: Benchmarking Coding Agents Beyond Issue Resolution*. arXiv. https://doi.org/10.48550/arxiv.2605.08366
26. Reem Aleithan, Xue, Haoran, Mohammad Mahdi Mohajer et al. (2024). *SWE-Bench+: Enhanced Coding Benchmark for LLMs*. arXiv. https://doi.org/10.48550/arxiv.2410.06992
27. Bin Yu, Yuxuan Zhu, Pinjia He et al. (2025). *UTBoost: Rigorous Evaluation of Coding Agents on SWE-Bench*. Proceedings of the conference - Association for Computational Linguistics. Meeting. https://doi.org/10.18653/v1/2025.acl-long.189
28. You Wang, Michael Pradel, Zhongxin Liu et al. (2026). *Are “Solved Issues” in SWE-bench Really Solved Correctly? An Empirical Study*. ACM/IEEE International Conference on Software Engineering: Companion Proceedings (ICSE-Companion). https://doi.org/10.1145/3744916.3764576
29. Boxi Yu, Yang Cao, Yuzhong Zhang et al. (2026). *SWE-ABS: Adversarial Benchmark Strengthening Exposes Inflated Success Rates on Test-based Benchmark*. International Conference on Machine Learning. https://doi.org/10.48550/arxiv.2603.00520
30. Spandan Garg, Benjamin Jeremiah Steenhoek, Yufan Huang et al. (2026). *Saving SWE-Bench: A Benchmark Mutation Approach for Realistic Agent Evaluation*. IEEE/ACM International Conference on AI Engineering – Software Engineering for AI (CAIN). https://doi.org/10.1145/3793653.3793762
31. Toufique Ahmed, Jatin Ganhotra, Avraham Shinnar et al. (2026). *Investigating Test Overfitting on SWE-bench*. ACM Joint European Software Engineering Conference and Symposium on the Foundations of Software Engineering (ESEC/FSE). https://doi.org/10.1145/3803437.3805574
32. Gustavo A. Oliva, Gopi Krishnan Rajbahadur, Aaditya Bhatia et al. (2025). *SPICE: An Automated SWE-Bench Labeling Pipeline for Issue Clarity, Test Coverage, and Effort Estimation*. IEEE/ACM International Conference on Automated Software Engineering (ASE). https://doi.org/10.1109/ase63991.2025.00192
33. Pujun Zheng, Zixin Shang, Shufan Jiang et al. (2026). *SWE-Bench Pro Verified: A Reliable Benchmark for Software Engineering Agents*. arXiv. https://doi.org/10.48550/arxiv.2609.08149
34. Mark Harman, Jillian Ritchey, Inna Harper et al. (2025). *Mutation-Guided LLM-based Test Generation at Meta*. ACM Joint European Software Engineering Conference and Symposium on the Foundations of Software Engineering (ESEC/FSE). https://doi.org/10.1145/3696630.3728544
35. Sanidhya Vijayvargiya, Xuhui Zhou, Akhila Yerukola et al. (2026). *Ambig-SWE: Interactive Agents to Overcome Underspecificity in Software Engineering*. International Conference on Learning Representations. https://doi.org/10.48550/arxiv.2502.13069
36. Shanchao Liang, Spandan Garg, Roshanak Zilouchian Moghaddam et al. (2026). *The SWE-Bench Illusion: When State-of-the-Art LLMs Remember Instead of Reason*. IEEE/ACM International Conference on Software Engineering: Software Engineering in Practice (ICSE-SEIP). https://doi.org/10.1145/3786583.3786882
37. Thanosan Prathifkumar, Noble Saji Mathews, Meiyappan Nagappan et al. (2025). *Does SWE-Bench-Verified Test Agent Ability or Model Memory?*. arXiv. https://doi.org/10.48550/arxiv.2512.10218
38. White, Colin, Samuel W. Dooley, Manley Roberts et al. (2025). *LiveBench: A Challenging, Contamination-Limited LLM Benchmark*. International Conference on Learning Representations. https://doi.org/10.48550/arxiv.2406.19314
39. Mike A. Merrill, Alexander Glenn Shaw, Nicholas Carlini et al. (2026). *Terminal-Bench: Benchmarking Agents on Hard, Realistic Tasks in Command Line Interfaces*. International Conference on Learning Representations. https://doi.org/10.48550/arxiv.2601.11868
40. Lei Zhang, Jiaxi Yang, Yang, Min et al. (2025). *SWE-Flow: Synthesizing Software Engineering Data in a Test-Driven Manner*. International Conference on Machine Learning. https://doi.org/10.48550/arxiv.2506.09003

**Tools used:** Kassis, T., Agarwal, V., He, Y., Patel, D., & Brueckner, A. (2026). *Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents*. arXiv:2609.00065. https://doi.org/10.48550/arXiv.2609.00065. Used the `literature-review` and `paper-lookup` skills, and the `scientific-critical-thinking` checklist for limitations.

**Not covered here:** Harbor's own design is documented at docs.harborframework.com (task format, `oracle`/`nop` agents, separate verifier, `harbor lint`/`check`), not in a peer-reviewed paper.
