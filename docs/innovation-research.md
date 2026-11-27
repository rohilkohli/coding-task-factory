# Innovation Research (round 3)

**Goal:** look beyond fixing weaknesses for directions that would set the factory apart: new task types, stronger grading, requirements, interaction, richer scoring and smarter evaluation.
**Method:** K-Dense *Scientific Agent Skills* `paper-lookup` (OpenAlex), 12 queries, publications from 2023 onward, top 40 by relevance each. That gave 448 new records (after removing rounds 1–2); 34 were screened in. Claims are taken from abstracts.
**Search date:** 2026-11-27. Query log: `docs/research-sources/round3_provenance.log`.

## What the factory already has that most benchmarks lack

For every task the factory knows the **exact defect location(s)**, holds a **set of validated, plausible wrong fixes**, and for multi-bug tasks knows **which tests belong to which defect**. The literature treats these as expensive extras. Here they are by-products, and the innovations below build on them.

## Innovation opportunities

| # | Idea | Evidence | What we would build | AI key? | Effort |
|---|---|---|---|---|---|
| **A** | **New task type: "write the test that catches this bug"**, graded by *rigor*, not just fail-to-pass | **Lax tests:** a test can fail on the bug and pass on the fix yet still accept plausible wrong patches. Only *rigorous* tests improve repair [4]. **Proactive testing is weak:** models find at most 16% of hidden defects with documentation as the oracle [2]. **Mutants as grader:** adversarial mutants and mutation games separate models well and resist contamination [1, 5]. **Property-based tests:** PBT-style test writing is a distinct, measurable skill [3, 10]. **Oracles:** generating correct, strong test oracles is itself hard [11]. **Benchmarks:** test-generation benchmarks exist, but they are function-level [6, 12]. | A **test-writing task** reuses each validated bug. The agent sees the buggy repo and a symptom, and must write a regression test. **Grading:** the test must fail on the bug, pass on the reference, and also fail on our hidden wrong fixes (rigor score). This is a second task family from the same factory with no new infrastructure. | **No** | Medium |
| **B** | **Per-defect partial credit** for multi-bug tasks, plus dense scores | Binary pass/fail wastes signal; dense and partial rewards give better evaluation and training signal [21, 22, 23]. Scope-weighted scoring measures partial recovery. | `reward.json` reports **which defects were fixed** (k of n), using each defect's own F2P tests. The factory already knows them. The binary reward is kept and partial credit is added. | **No** | Low |
| **C** | **Rigor certificate per task** | **Checklist:** 672 code benchmarks surveyed; quality practice lags awareness; HOW2BENCH gives 55 checks [24]. **Mutation-kill floor:** report the share of seeded mutants each testbench catches; 72% of one widely used benchmark's designs fell below a 95% kill floor [7]. **Disclosure:** a four-field protocol, where "unknown" is allowed [25]. **Natural-language checks:** quality criteria can be written as checkable statements [13]. | A generated `RIGOR.md` (and JSON) per task set covering the HOW2BENCH-style checks we satisfy (coverage of the changed code, mutation kill rate, flaky checks, reproducibility, provenance) and a contamination disclosure. It turns our checks into a visible quality certificate. | **No** | Low |
| **D** | **Interactive, under-specified tasks with a simulated user** | **Multi-turn gap:** single-turn success does not carry over to multi-turn, user-driven sessions (about 50% vs 25%) [16]; stronger agents also need fewer corrections from the user [15]. **Asking questions is a separate skill:** agents rush into implementation or over-ask [14, 18, 20], and real-world misalignment is mostly about intent [19]. **Harbor fit:** user simulators have been built *on Harbor* [17]; Harbor ships a `--user-agent` option. | A "vague request" variant of each feature task: a short instruction, with the full requirements held by a simulated user persona. This tests whether the agent asks the right questions. It also addresses the "requirements" part of the challenge. | **Yes** (simulated user) | Medium |
| **E** | **Localisation-aware failure analysis** | **Early failure:** failures start early and come from epistemic errors [30]. **Localisation:** failed runs often still find the right file (72–81%) [29]. **Behaviour:** trajectories reveal success and failure motifs [28, 31]. | Because we know the exact injected location, each agent run can be scored for **"found the right function?" vs "fixed it?"**, separating search failures from coding failures. | **Yes** (agent runs) | Low once runs exist |
| **F** | **Adaptive testing for cheap, reliable evaluation** | IRT plus adaptive item selection reproduces full rankings with about 3% of items while covering difficulty [26]; there is a survey of ML-based adaptive testing [27]. | Once agent results exist, select the most informative tasks per model and report ability estimates instead of raw pass rates. | **Yes** (agent runs) | Low |
| **G** | **Code-review tasks** | Review agents solve about 40% of review tasks built from human reviews [32]; checklist-based review grading exists [33]; refactoring tasks check structure as well as tests [34]. | Present a pull request containing one of our validated bugs plus benign edits, and grade whether the review flags the defective hunk. | No for grading; benign edits need care | High |
| **H** | **Differential testing as extra grading** | LLM-guided search finds inputs that separate two program versions for 81.7% of pairs [8]; semantic features detect overfitting patches [9]. | Compare the agent's function with the reference on generated inputs. This is hard to do generically for repo-level APIs, so it is lower priority. | Yes | High |

## Recommendation (deadline 6 Dec)

**Build now (no key needed):**
1. **A: "write the rigorous test" tasks.** This is the most distinctive idea and the best fit for the factory. It adds a second task family (Meaningful Variation) and an original grading idea (Originality & Engineering), using assets only this pipeline has. Start with click (Python), then extend if time allows.
2. **B: per-defect partial credit.** Low effort, and it gives richer evaluation output for the demo.
3. **C: rigor certificate.** Low effort, high clarity for judges (Practical Impact & Clarity, Accuracy & Validation).

**With an AI key:**
- **D:** interactive vague-request variants.
- **E and F:** real agent runs with localisation analysis and adaptive or IRT reporting.

## Limitations
- **Coverage:** OpenAlex only, top 40 per query, title screening, abstract-level extraction.
- **Unverified claims:** many sources are 2026 preprints with self-reported results.
- **Not a novelty proof:** this is a scoping review, not proof that no similar system exists.

## References

1. Pengyu Chang, Yixiong Fang, SILIN CHEN et al. (2026). *Test vs Mutant: Adversarial LLM Agents for Robust Unit Test Generation*. Proceedings of the ACM on software engineering.. https://doi.org/10.1145/3832122
2. Steven Liu, Jane Luo, Xin Zhang et al. (2026). *TestExplora: Benchmarking LLMs for Proactive Bug Discovery via Repository-Level Test Generation*. International Conference on Machine Learning. https://doi.org/10.48550/arxiv.2602.10471
3. Lucas Jing, Xinqi Wang, Liao Zhang et al. (2026). *PBT-Bench: Benchmarking AI Agents on Property-Based Testing*. arXiv. https://doi.org/10.48550/arxiv.2605.15229
4. Yuhao Tan, Zhibang Yang, Fangkai Yang et al. (2026). *Beyond Fail-to-Pass: Iterative Hardening of Co-Generated Bug Reproduction Tests and Fixes*. arXiv. https://doi.org/10.48550/arxiv.2607.19843
5. Artur Romazanov, Gordon Fraser, Steffen Herbold et al. (2026). *CDBench: Benchmarking the mutation testing capabilities of LLMs with code defenders*. Empirical Software Engineering. https://doi.org/10.1007/s10664-026-10901-8
6. Dong Huang, Jie M. Zhang, Mark Harman et al. (2026). *Benchmarking LLMs for Unit Test Generation from Real-World Functions*. ACM Transactions on Software Engineering and Methodology. https://doi.org/10.1145/3805043
7. Meet Bhadra (2026). *GateTruth: Auditing the Rigor of RTL Design Benchmarks via Mutation Testing*. arXiv. https://doi.org/10.48550/arxiv.2608.12635
8. Khashayar Etemadi, Bardia Mohammadi, Zhendong Su et al. (2025). *Mokav: Execution-driven differential testing with LLMs*. Journal of Systems and Software. https://doi.org/10.1016/j.jss.2025.112571
9. Dowon Song, Hakjoo Oh (2025). *Enhancing APR with PRISM: A Semantic-Based Approach to Overfitting Patch Detection*. Proceedings of the ACM on Programming Languages. https://doi.org/10.1145/3763170
10. Vasudev Vikram, Caroline Lemieux, Joshua S. Sunshine et al. (2023). *Can Large Language Models Write Good Property-Based Tests?*. arXiv. https://doi.org/10.48550/arxiv.2307.04346
11. Soneya Binta Hossain, Matthew B. Dwyer (2025). *TOGLL: Correct and Strong Test Oracle Generation with LLMS*. ACM/IEEE International Conference on Software Engineering: Companion Proceedings (ICSE-Companion). https://doi.org/10.1109/icse55347.2025.00098
12. Wenhan Wang, Chenyuan Yang, Zhijie Wang et al. (2025). *TESTEVAL: Benchmarking Large Language Models for Test Case Generation*. Findings of the Association for Computational Linguistics: NAACL. https://doi.org/10.18653/v1/2025.findings-naacl.197
13. Jon Saad-Falcon, Rajan Vivek, William Berrios et al. (2024). *LMUnit: Fine-grained Evaluation with Natural Language Unit Tests*. arXiv. https://doi.org/10.48550/arxiv.2412.13091
14. Hao Wang, Ligong Han, Kai Xu et al. (2026). *Turning Intent into Specifications: A Benchmark and an Interactive User-Assistant Agent*. arXiv. https://doi.org/10.48550/arxiv.2606.20585
15. Yifan Wu, Z. Zhao, Songlin Li et al. (2026). *SWE-Together: Evaluating Coding Agents in Interactive User Sessions*. arXiv. https://doi.org/10.48550/arxiv.2606.29957
16. Mohit Raghavendra, Anisha Gunjal, Aakash Sabharwal et al. (2026). *SWE-INTERACT: Reimagining SWE Benchmarks as User-Driven Long-Horizon Coding Sessions*. arXiv. https://doi.org/10.48550/arxiv.2606.30573
17. Lorenz Brehme, Benjamin Jeremiah Steenhoek, Ruth Breu et al. (2026). *SWE-DIVE: Multi-Turn Coding Agent Evaluation with Dynamic User Simulation*. arXiv. https://doi.org/10.48550/arxiv.2610.30047
18. Nicholas Edwards, Sebastian Schuster (2026). *Ask or Assume? Uncertainty-Aware Clarification-Seeking in Coding Agents*. Findings of the Association for Computational Linguistics: EMNLP (Findings of EMNLP). https://doi.org/10.18653/2026.findings-emnlp.15
19. Ningzhi Tang, Chaoran Chen, Gelei Xu et al. (2026). *How Coding Agents Fail Their Users: A Large-Scale Analysis of Developer-Agent Misalignment in 20,574 Real-World Sessions*. Conference on Empirical Methods in Natural Language Processing (EMNLP). https://doi.org/10.18653/2026.emnlp-main.1011
20. Zheng Fang, Dongming Jin, Y H Dong et al. (2026). *ClarifyCodeBench: Evaluating LLMs on Clarifying Ambiguous Requirements for Code Generation*. arXiv. https://doi.org/10.48550/arxiv.2607.00711
21. Jihan Yao, Sihan Zeng, Shangbin Feng et al. (2026). *Before the Rollout Ends: Early Terminal Reward Prediction for Long-horizon Coding Agents*. arXiv. https://doi.org/10.48550/arxiv.2609.31995
22. Jingxuan Xu, Gang Wu, Yanan Wu et al. (2026). *FLARE: A Full-Lifecycle Dense Supervision Paradigm for Long-Horizon Coding Agents via Generative Reward Model*. arXiv. https://doi.org/10.48550/arxiv.2609.23808
23. Liang Ding (2026). *AdaRubric: Task-Adaptive Rubrics for Reliable LLM Agent Evaluation and Reward Learning*. arXiv. https://doi.org/10.48550/arxiv.2603.21362
24. Jialun Cao, Chan, Yuk-Kit, Zixuan Ling et al. (2026). *Code Benchmarks Should Prioritize Rigor, Reliability, and Reproducibility*. International Conference on Machine Learning. https://doi.org/10.48550/arxiv.2501.10711
25. Johanna Angulo, Víctor Yeste, Héctor Espinós-Morató et al. (2026). *Benchmark Contamination: A Taxonomy Organized by Defeated Mitigation*. arXiv. https://doi.org/10.48550/arxiv.2608.29463
26. Ziliang Pang, Tianhe Wang, Tianshu Yu et al. (2026). *FAIR-Eval: Reliable and Efficient Adaptive Benchmarking for Large Language Models*. Findings of the Association for Computational Linguistics: EMNLP (Findings of EMNLP). https://doi.org/10.18653/2026.findings-emnlp.1980
27. Yan Zhuang, Qi Liu, Haoyang Bi et al. (2026). *Survey of Computerized Adaptive Testing: A Machine Learning Perspective*. IEEE Transactions on Pattern Analysis and Machine Intelligence. https://doi.org/10.1109/tpami.2026.3672850
28. Islem Bouzenia, Michael Pradel (2025). *Understanding Software Engineering Agents: A Study of Thought-Action-Result Trajectories*. IEEE/ACM International Conference on Automated Software Engineering (ASE). https://doi.org/10.1109/ase63991.2025.00234
29. Oorja Majgaonkar, Zhiwei Fei, Xiang Li et al. (2025). *Understanding Code Agent Behaviour: An Empirical Study of Success and Failure Trajectories*. arXiv. https://doi.org/10.48550/arxiv.2511.00197
30. X Zhao, Han Li, Shuaiting Li et al. (2026). *Failure as a Process: An Anatomy of CLI Coding Agent Trajectories*. arXiv. https://doi.org/10.48550/arxiv.2607.09510
31. Razvan Mihai Popescu (2026). *Reliable and Developer-Aligned Evaluation of Agents for Software Engineering*. ACM Joint European Software Engineering Conference and Symposium on the Foundations of Software Engineering (ESEC/FSE). https://doi.org/10.1145/3803437.3804877
32. Yuntong Zhang, Zhiyuan Pan, Imam Nur Bani Yusuf et al. (2026). *Code Review Agent Benchmark*. arXiv. https://doi.org/10.48550/arxiv.2603.23448
33. Daoan Zhang, Shuo Zhang, Zijian Jin et al. (2026). *Sphinx: Benchmarking and Modeling for LLM-Driven Pull Request Review*. arXiv. https://doi.org/10.48550/arxiv.2601.04252
34. Alex Thillen, Niels Mündler, Veselin Raychev et al. (2026). *CodeTaste: Can LLMs Generate Human-Level Code Refactorings?*. International Conference on Machine Learning. https://doi.org/10.48550/arxiv.2603.04177
