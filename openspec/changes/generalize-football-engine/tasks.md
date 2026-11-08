# Tasks

Nothing below is authorised until this change is merged into `main` by a human. Estimates are
planning guesses in person-days (pd). Owners are proposals. **human-local** means a person runs the
step on match data and reports only hashes, pass/fail or aggregates. A task may close with a recorded
rejection when its *Done when* allows it.

## 1. P0: valid, testable, game-independent engine

- [ ] 1.1 Open the compliance log and draft organiser questions
  - **Objective:** Record the findings and the questions a human will send.
  - **Priority:** P0
  - **Estimate:** 0.25 pd
  - **Owner:** Raúl, reviewed by all
  - **Depends on:** none
  - **Files:** docs/engine/compliance-log.md, docs/engine/organiser-questions.md, tests/compliance/test_compliance_log.py
  - **Requirements:** Compliance questions are escalated and logged
  - **Verification:** `pytest tests/compliance/test_compliance_log.py`; human review
  - **Done when:** The log lists every finding and the team has decided who sends the questions and when

- [ ] 1.2 Pin the environment and make gates fail for real
  - **Objective:** Lockfile, pytest in CI, `--test-all` exits non-zero on failure.
  - **Priority:** P0
  - **Estimate:** 0.75 pd
  - **Owner:** Raúl
  - **Depends on:** none
  - **Files:** pyproject.toml, uv.lock, requirements.txt, run_experiment.py, tools/pre_commit.py, .github/workflows/ci.yml, tests/engine/test_test_all.py
  - **Requirements:** Pinned environment, Effective quality gates
  - **Verification:** `pytest tests/engine/test_test_all.py`; CI red on a deliberately failing fake strategy
  - **Done when:** CI installs from the lockfile and fails when a strategy fails

- [ ] 1.3 Build the seeded synthetic match generator
  - **Objective:** Known-truth matches long enough to reach every engine phase.
  - **Priority:** P0
  - **Estimate:** 1 pd
  - **Owner:** Third member
  - **Depends on:** none
  - **Files:** tests/synthetic/generator.py, tests/synthetic/test_generator.py
  - **Requirements:** Engine stages are reachable by tests
  - **Verification:** `pytest tests/synthetic`
  - **Done when:** Same seed gives identical matches with passes, flights, touches, occlusions, stoppages, kickoffs and end swaps

- [ ] 1.4 Add static compliance tests
  - **Objective:** Detect match literals, club names, frame-window assertions and public-GT gates.
  - **Priority:** P0
  - **Estimate:** 0.5 pd
  - **Owner:** Raúl
  - **Depends on:** 1.1
  - **Files:** tests/compliance/test_static_compliance.py, tests/compliance/allowlist.toml
  - **Requirements:** No match-specific constants in inference, No hand labels on the provided game, Public ground truth limited to pipeline checks, Full-match labels stay out of Git
  - **Verification:** `pytest tests/compliance` with seeded violations in temporary fixtures
  - **Done when:** Each prohibited pattern is detected; current violations are listed as expected failures that later tasks remove

- [ ] 1.5 Retire golden frame tests, label snapshot and public gates
  - **Objective:** Remove frame expectations, the tracked snapshot, the metric floor, the sweep and automatic public scoring and logging.
  - **Priority:** P0
  - **Estimate:** 0.5 pd
  - **Owner:** Jordi, with Raúl
  - **Depends on:** 1.1, 1.4
  - **Files:** tests/test_golden_spells.py, tests/baseline/football_engine_segments.json, tools/regression_check.py, tools/sweep_hysteresis.py, tools/agent_eval.py, run_experiment.py, experiments/README.md, AGENTS.md, DEVELOPING.md, docs/engine/compliance-log.md
  - **Requirements:** No hand labels on the provided game, Public ground truth limited to pipeline checks, Full-match labels stay out of Git
  - **Verification:** `pytest tests/compliance`; `git log --follow` still shows removed files
  - **Done when:** No gate uses a public metric or a frame expectation, and each removal is logged

- [ ] 1.6 Add game configuration and one loader
  - **Objective:** `GameConfig`, a single ingestion path and an optional hash-keyed cache.
  - **Priority:** P0
  - **Estimate:** 1 pd
  - **Owner:** Raúl
  - **Depends on:** none
  - **Files:** games.py, pipeline/ingest.py, pipeline/runner.py, run_experiment.py, strategies/base.py, tests/engine/test_ingest.py, tests/submission/test_cache.py
  - **Requirements:** Game configuration holds only published facts, Cache semantics
  - **Verification:** `pytest tests/engine/test_ingest.py tests/submission/test_cache.py`; human-local array hash equal to the former loader
  - **Done when:** No path silently prefers a cache and output is equal with and without cache

- [ ] 1.7 Infer match facts
  - **Objective:** Attack direction, kicking team and tracklet team from tracking.
  - **Priority:** P0
  - **Estimate:** 1.25 pd
  - **Owner:** Jordi
  - **Depends on:** 1.3, 1.6
  - **Files:** pipeline/match_facts.py, tests/engine/test_match_facts.py
  - **Requirements:** Match facts are inferred
  - **Verification:** `pytest tests/engine/test_match_facts.py`; human-local check that inferred facts agree with published ones, reporting pass/fail only
  - **Done when:** End swaps, goalkeeper mislabels, kickoffs and unknown cases behave as specified

- [ ] 1.8 Remove class-A constants and fix missing values
  - **Objective:** Replace frame, side, team and slot literals with config and inferred facts; NaN-safe speeds and distances.
  - **Priority:** P0
  - **Estimate:** 1.25 pd
  - **Owner:** Jordi
  - **Depends on:** 1.4, 1.7
  - **Files:** strategies/football_engine.py, pipeline/dead_ball.py, tests/engine/test_equivariance.py, tests/engine/test_missing_values.py
  - **Requirements:** No match-specific constants in inference, Equivariance, Missing observations stay missing
  - **Verification:** `pytest tests/compliance tests/engine`; human-local count of changed frames versus the previous output, count only
  - **Done when:** Inference expected failures are gone and mirror, swap and permutation tests pass

- [ ] 1.9 Add the single entrypoint and manifest
  - **Objective:** `make_submission.py` with config, validation, atomic write and manifest.
  - **Priority:** P0
  - **Estimate:** 0.75 pd
  - **Owner:** Raúl
  - **Depends on:** 1.2, 1.6
  - **Files:** make_submission.py, pipeline/submission.py, config/engine.toml, tests/submission/test_entrypoint.py
  - **Requirements:** Single submission entrypoint, Deterministic output, Versioned parameters, Input validation and error handling, Run manifest, Contract verification before success
  - **Verification:** `pytest tests/submission`
  - **Done when:** A synthetic run gives a valid file, equal hashes on two runs, and a manifest with no labels or coordinates

- [ ] 1.10 Produce the G1 fallback
  - **Objective:** Generate the compliant fallback from a clean clone and tag it.
  - **Priority:** P0
  - **Estimate:** 0.25 pd
  - **Owner:** Jordi (human-local)
  - **Depends on:** 1.5, 1.8, 1.9
  - **Files:** docs/engine/release-log.md, tests/compliance/test_release_log.py
  - **Requirements:** Deterministic output, Contract verification before success
  - **Verification:** Human-local: two clean runs with equal SHA-256 and the official validator passing; `pytest tests/compliance/test_release_log.py`
  - **Done when:** Tag, hash and validator result are recorded, with no labels committed

## 2. P1: measure generalisation and improve on evidence

- [ ] 2.1 Give every rule an identifier, a switch and a register entry
  - **Objective:** Make each post-processing rule switchable and classify it A, B or C.
  - **Priority:** P1
  - **Estimate:** 1 pd
  - **Owner:** Jordi
  - **Depends on:** 1.8
  - **Files:** strategies/football_engine.py, config/engine.toml, docs/engine/rule-register.toml, tests/engine/test_rules.py
  - **Requirements:** Rules are identified and switchable, Rule register, Engine stages are reachable by tests
  - **Verification:** `pytest tests/engine/test_rules.py`
  - **Done when:** All-off equals the base FSM; each rule is triggered by a synthetic case; every rule has an entry

- [ ] 2.2 Register datasets and write the Metrica adapter
  - **Objective:** Register public datasets, download by script, convert Metrica sample games.
  - **Priority:** P1
  - **Estimate:** 1.25 pd
  - **Owner:** Third member
  - **Depends on:** 1.6
  - **Files:** validation/datasets.toml, validation/acquire.py, validation/adapters/metrica.py, tests/validation/test_register.py, tests/validation/test_adapters.py, tests/validation/fixtures/
  - **Requirements:** Authorised dataset register, Adapters target the engine's input
  - **Verification:** `pytest tests/validation`
  - **Done when:** Metrica games load with a quality report, and unregistered and competition data are refused

- [ ] 2.3 Build reference labels
  - **Objective:** Derive H, A and D from events in two versioned variants with ambiguity masks.
  - **Priority:** P1
  - **Estimate:** 1 pd
  - **Owner:** Third member
  - **Depends on:** 2.2
  - **Files:** validation/references.py, tests/validation/test_references.py
  - **Requirements:** Reference labels declare their uncertainty
  - **Verification:** `pytest tests/validation/test_references.py`
  - **Done when:** Both variants are documented and their differences reported

- [ ] 2.4 Implement corruption
  - **Objective:** Seeded ball dropout near duels and flights, tracklet fragmentation and swaps, team noise, coordinate noise.
  - **Priority:** P1
  - **Estimate:** 0.5 pd
  - **Owner:** Third member
  - **Depends on:** 2.2
  - **Files:** validation/corruptions.py, tests/validation/test_corruptions.py
  - **Requirements:** Realistic corruption
  - **Verification:** `pytest tests/validation/test_corruptions.py`
  - **Done when:** Same seed gives the same data and zero strength equals adapter output

- [ ] 2.5 Build the benchmark and freeze the suite
  - **Objective:** Per-game official metrics, paired bootstrap, baseline, corruption; suite hash recorded before comparisons.
  - **Priority:** P1
  - **Estimate:** 0.75 pd
  - **Owner:** Third member, with Raúl
  - **Depends on:** 2.3, 2.4
  - **Files:** validation/benchmark.py, validation/suite.toml, tests/validation/test_benchmark.py
  - **Requirements:** Comparable reporting, Selection rule
  - **Verification:** `pytest tests/validation/test_benchmark.py`; `python -m validation.benchmark --suite smoke`
  - **Done when:** The report has all required fields and the suite hash is in the decision log

- [ ] 2.6 Take the first external measurement
  - **Objective:** Measure the G1 engine and the baseline on the external suite.
  - **Priority:** P1
  - **Estimate:** 0.25 pd
  - **Owner:** Third member
  - **Depends on:** 1.10, 2.5
  - **Files:** docs/engine/decisions.md, tests/validation/test_decision_log.py
  - **Requirements:** Comparable reporting
  - **Verification:** `python -m validation.benchmark --suite external`; `pytest tests/validation/test_decision_log.py`
  - **Done when:** Results per game, with intervals and the unknown competition score, are recorded

- [ ] 2.7 Build and run the label-free audit
  - **Objective:** Aggregate audit: rules inside versus outside the public window, spell statistics, perturbation stability.
  - **Priority:** P1
  - **Estimate:** 1 pd
  - **Owner:** Raúl, run by Jordi (human-local)
  - **Depends on:** 2.1
  - **Files:** tools/match_audit.py, tests/engine/test_match_audit.py, docs/engine/decisions.md
  - **Requirements:** Aggregate-only output, Inside versus outside the public window, Stability under perturbation, Audit is diagnostic, not a target
  - **Verification:** `pytest tests/engine/test_match_audit.py` on synthetic data; human-local run with only the aggregate summary shared
  - **Done when:** Flags are reviewed and listed in the decision log

- [ ] 2.8 Ablate rules and decide
  - **Objective:** Turn each rule off on the external suite and decide keep, change or remove.
  - **Priority:** P1
  - **Estimate:** 1 pd
  - **Owner:** Jordi and third member
  - **Depends on:** 2.1, 2.6, 2.7
  - **Files:** docs/engine/rule-register.toml, docs/engine/decisions.md, config/engine.toml, tests/engine/test_rules.py
  - **Requirements:** Rule register, Selection rule
  - **Verification:** `python -m validation.benchmark --suite external --ablate-rules`; `pytest tests/engine/test_rules.py`
  - **Done when:** Every rule has a recorded decision; class-B rules without evidence are off by default unless a recorded decision says otherwise

- [ ] 2.9 Improve the engine on external failures
  - **Objective:** Change rules or add game-independent logic for failure modes seen in external games, behind switches.
  - **Priority:** P1
  - **Estimate:** 2 pd
  - **Owner:** Jordi, with third member
  - **Depends on:** 2.8
  - **Files:** strategies/football_engine.py, pipeline/dead_ball.py, pipeline/evidence.py, config/engine.toml, docs/engine/rule-register.toml, docs/engine/decisions.md, tests/engine/test_rules.py
  - **Requirements:** Evidence-driven engine changes, Selection rule
  - **Verification:** `pytest tests/engine`; `python -m validation.benchmark --suite external`
  - **Done when:** Each change is adopted or rejected by the selection rule and logged; rejected changes stay off

- [ ] 2.10 Freeze the algorithm (G2)
  - **Objective:** Record the final configuration and the evidence for it.
  - **Priority:** P1
  - **Estimate:** 0.25 pd
  - **Owner:** All
  - **Depends on:** 2.8, 2.9
  - **Files:** docs/engine/decisions.md, config/engine.toml, tests/validation/test_decision_log.py
  - **Requirements:** Selection rule, Rule register
  - **Verification:** `pytest tests/validation/test_decision_log.py`
  - **Done when:** The decision log names the frozen configuration and its external results

- [ ] 2.11 Align documents and rehearse the release
  - **Objective:** Correct `APPROACH.md`, agent guidance and the technical document; clean-clone rehearsal.
  - **Priority:** P1
  - **Estimate:** 1 pd
  - **Owner:** All (human-local for the run)
  - **Depends on:** 2.10
  - **Files:** APPROACH.md, DEVELOPING.md, AGENTS.md, .agents/skills/possession-pipeline/SKILL.md, docs/engine/release-log.md, tests/compliance/test_docs.py
  - **Requirements:** Technical document matches the repository, Compliance questions are escalated and logged, Single submission entrypoint, Deterministic output
  - **Verification:** `pytest tests/compliance`; human-local clean-clone regeneration with identical hash and official validator
  - **Done when:** Document statements match the logs, blocking questions are closed, and a human holds the deliverables

## 3. P2: optional, only if P1 is on schedule

- [ ] 3.1 Add the IDSSE adapter
  - **Objective:** A second independent provider in the suite.
  - **Priority:** P2
  - **Estimate:** 1 pd
  - **Owner:** Third member
  - **Depends on:** 2.5
  - **Files:** validation/adapters/idsse.py, validation/datasets.toml, tests/validation/test_adapters.py
  - **Requirements:** Adapters target the engine's input, Authorised dataset register
  - **Verification:** `pytest tests/validation/test_adapters.py`
  - **Done when:** IDSSE games run in the benchmark, or the attempt is recorded as dropped

- [ ] 3.2 Clean the subtitle viewer
  - **Objective:** Remove constants and the public-GT overlay; keep it a local viewer.
  - **Priority:** P2
  - **Estimate:** 0.5 pd
  - **Owner:** Raúl
  - **Depends on:** 1.8
  - **Files:** tools/generate_subtitles.py, tests/engine/test_subtitles.py
  - **Requirements:** No match-specific constants in inference, Public ground truth limited to pipeline checks
  - **Verification:** `pytest tests/engine/test_subtitles.py tests/compliance`
  - **Done when:** The viewer runs on synthetic data and the compliance scan passes

- [ ] 3.3 Measure run time and memory
  - **Objective:** Record budgets for the full-length synthetic run.
  - **Priority:** P2
  - **Estimate:** 0.25 pd
  - **Owner:** Raúl
  - **Depends on:** 1.9
  - **Files:** tests/submission/test_performance.py, config/engine.toml
  - **Requirements:** Resource budget
  - **Verification:** `pytest tests/submission/test_performance.py`
  - **Done when:** Budgets are recorded and the test enforces them

## 4. P3: after phase 1

- [ ] 4.1 Close the change
  - **Objective:** Archive the change and list deferred ideas (probabilistic decoders, ball reconstruction, video) as unapproved.
  - **Priority:** P3
  - **Estimate:** 0.25 pd
  - **Owner:** Raúl
  - **Depends on:** 2.11
  - **Files:** docs/engine/decisions.md, tests/validation/test_decision_log.py
  - **Requirements:** Rule register
  - **Verification:** `openspec validate --all --strict --no-interactive`; governance checker with `--change generalize-football-engine`
  - **Done when:** `verification.md` is COMPLETE and the change is archived
