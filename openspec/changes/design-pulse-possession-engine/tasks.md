# Tasks

Nothing below is authorised until this change is merged into `main` by a human. Priorities: group 1 =
P0, group 2 = P1, group 3 = P2, group 4 = P3. Estimates are planning guesses in person-days (pd), not
measurements. Owners are proposals. **human-local** means the step needs match data, so a person runs
it and reports only pass/fail or hashes. Tasks may close with a recorded rejection when their
*Done when* allows it: evidence decides what stays.

## 1. P0: Compliance and reproducibility

- [ ] 1.1 Open the compliance log and draft organiser questions
  - **Objective:** Record the issues in `supporting/current-architecture.md` and prepare the questions a human will send.
  - **Priority:** P0
  - **Estimate:** 0.25 pd
  - **Owner:** Raúl, reviewed by all
  - **Depends on:** none
  - **Files:** docs/pulse/compliance-log.md, docs/pulse/organiser-questions.md
  - **Requirements:** Compliance questions are escalated and logged
  - **Verification:** Human review; `tests/compliance/test_compliance_log.py` checks required headings
  - **Done when:** The log lists each item, and maintainers have recorded who sends the questions and when

- [ ] 1.2 Build the seeded synthetic match generator
  - **Objective:** Provide known-truth matches long enough to reach every engine stage.
  - **Priority:** P0
  - **Estimate:** 1.5 pd
  - **Owner:** Third member
  - **Depends on:** none
  - **Files:** tests/synthetic/generator.py, tests/synthetic/test_generator.py
  - **Requirements:** Effective quality gates
  - **Verification:** `pytest tests/synthetic`
  - **Done when:** The same seed gives identical matches covering passes, flights, touches, occlusions, stoppages and tags

- [ ] 1.3 Make test commands and CI fail for real
  - **Objective:** Fix `--test-all`, add pytest to CI and stop counting skips as passes.
  - **Priority:** P0
  - **Estimate:** 0.5 pd
  - **Owner:** Raúl
  - **Depends on:** 1.2
  - **Files:** run_experiment.py, tools/pre_commit.py, .github/workflows/ci.yml, tests/strategies/test_test_all.py
  - **Requirements:** Effective quality gates
  - **Verification:** `pytest tests/strategies/test_test_all.py` proves a failing fake strategy gives a non-zero exit
  - **Done when:** A deliberately failing strategy turns the command and CI red

- [ ] 1.4 Pin the environment
  - **Objective:** Python 3.11 and a lockfile, with documented installation.
  - **Priority:** P0
  - **Estimate:** 0.25 pd
  - **Owner:** Raúl
  - **Depends on:** none
  - **Files:** pyproject.toml, uv.lock, requirements.txt, DEVELOPING.md
  - **Requirements:** Pinned environment
  - **Verification:** `uv sync --frozen` on a clean clone, then `uv pip freeze` compared with the lockfile
  - **Done when:** CI installs from the lockfile and the official scorer still runs unchanged

- [ ] 1.5 Add static compliance tests
  - **Objective:** Detect match constants, club names, frame-window assertions and public-GT gates.
  - **Priority:** P0
  - **Estimate:** 0.75 pd
  - **Owner:** Raúl
  - **Depends on:** 1.1
  - **Files:** tests/compliance/test_static_compliance.py, tests/compliance/allowlist.toml
  - **Requirements:** No match-specific constants in inference, No hand labels on the provided game, Public ground truth limited to pipeline checks, Full-match labels stay out of Git
  - **Verification:** `pytest tests/compliance` with seeded violations in temporary fixtures
  - **Done when:** Each prohibited pattern is detected in a fixture; known current violations are listed as expected failures that later tasks remove

- [ ] 1.6 Retire golden frame tests, label snapshot and public gates
  - **Objective:** Remove human frame expectations, the tracked label snapshot, metric floors and the public sweep from the working tree.
  - **Priority:** P0
  - **Estimate:** 0.5 pd
  - **Owner:** Jordi, with Raúl
  - **Depends on:** 1.1, 1.5
  - **Files:** tests/test_golden_spells.py, tests/baseline/football_engine_segments.json, tools/regression_check.py, tools/sweep_hysteresis.py, run_experiment.py, AGENTS.md, DEVELOPING.md, experiments/README.md, docs/pulse/compliance-log.md, tests/tools/test_regression_check.py
  - **Requirements:** No hand labels on the provided game, Public ground truth limited to pipeline checks, Full-match labels stay out of Git, Compliance questions are escalated and logged
  - **Verification:** `pytest tests/compliance tests/tools`; `git log --follow` still shows the removed files
  - **Done when:** Gates contain no public metric or frame expectation, and the log links each removal

- [ ] 1.7 Define contracts and game configuration
  - **Objective:** Add the typed layers and validation, with an adapter to `TrackingContext`.
  - **Priority:** P0
  - **Estimate:** 1 pd
  - **Owner:** Raúl
  - **Depends on:** none
  - **Files:** pipeline/contracts.py, games.py, strategies/base.py, tests/pipeline/test_contracts.py
  - **Requirements:** Frame and time indexing, Coordinate and unit conventions, Missing observations are explicit, Separated data layers with provenance, Contract validation
  - **Verification:** `pytest tests/pipeline/test_contracts.py`
  - **Done when:** Every contract rejects its documented invalid inputs and existing strategies still run through the adapter

- [ ] 1.8 Unify ingestion and remove the implicit cache
  - **Objective:** One loader for tracking, metadata and tags; an optional, hash-keyed cache.
  - **Priority:** P0
  - **Estimate:** 1 pd
  - **Owner:** Raúl
  - **Depends on:** 1.7
  - **Files:** pipeline/ingest.py, pipeline/runner.py, run_experiment.py, tests/pipeline/test_ingest.py, tests/submission/test_cache.py
  - **Requirements:** Single ingestion path, Cache semantics
  - **Verification:** `pytest tests/pipeline/test_ingest.py tests/submission/test_cache.py`; human-local hash of arrays compared with the former loader
  - **Done when:** No code path silently prefers a cache, and synthetic output is equal with and without cache

- [ ] 1.9 Infer match facts
  - **Objective:** Direction, kicking team and tracklet team from tracking.
  - **Priority:** P0
  - **Estimate:** 1.5 pd
  - **Owner:** Jordi
  - **Depends on:** 1.7
  - **Files:** pipeline/match_facts.py, tests/pipeline/test_match_facts.py
  - **Requirements:** Inferred match facts, Inferred team assignment for tracklets, Tracklets are not identities
  - **Verification:** `pytest tests/pipeline/test_match_facts.py`; human-local check that inference is consistent with the published facts, reporting pass/fail only
  - **Done when:** Synthetic end swaps, goalkeeper mislabels and unknown cases behave as specified

- [ ] 1.10 Remove class-A constants from inference
  - **Objective:** Replace frame, side, team and slot literals with config and inferred facts, and repair undefined-speed handling.
  - **Priority:** P0
  - **Estimate:** 1.5 pd
  - **Owner:** Jordi
  - **Depends on:** 1.5, 1.9
  - **Files:** strategies/football_engine.py, pipeline/dead_ball.py, tools/generate_subtitles.py, tests/strategies/test_engine_properties.py
  - **Requirements:** No match-specific constants in inference, Mirror and team-swap equivariance, Missing observations are explicit
  - **Verification:** `pytest tests/compliance tests/strategies/test_engine_properties.py`; human-local comparison of the differing frame count against the previous output, reporting the count only
  - **Done when:** Compliance expected failures for inference are gone and mirror, swap and slot-permutation tests pass

- [ ] 1.11 Add the single submission entrypoint and manifest
  - **Objective:** `make_submission.py` with config, validation, atomic write and manifest; retire `pipeline/runner.py`.
  - **Priority:** P0
  - **Estimate:** 1 pd
  - **Owner:** Raúl
  - **Depends on:** 1.4, 1.8
  - **Files:** make_submission.py, pipeline/submission.py, pipeline/runner.py, config/pulse.toml, tests/submission/test_entrypoint.py
  - **Requirements:** Single submission entrypoint, Deterministic output, Versioned parameters, Input validation and error handling, Run manifest, Contract verification before success, Resource budget
  - **Verification:** `pytest tests/submission`, including two-run hash equality and a failure leaving no final file
  - **Done when:** The synthetic run produces a valid file and a manifest with no labels or coordinates

- [ ] 1.12 Classify every rule and create the provenance register
  - **Objective:** Assign each engine rule and parameter a class, rationale, origin and status.
  - **Priority:** P0
  - **Estimate:** 0.75 pd
  - **Owner:** Jordi, reviewed by Raúl
  - **Depends on:** 1.1
  - **Files:** docs/pulse/rule-register.toml, tests/compliance/test_rule_register.py
  - **Requirements:** Rule provenance register
  - **Verification:** `pytest tests/compliance/test_rule_register.py`
  - **Done when:** Every rule identifier has an entry and class-B decisions have an owner

- [ ] 1.13 Align the technical document and agent guidance
  - **Objective:** Correct compliance and reproduction statements, and hardcoded guidance for agents.
  - **Priority:** P0
  - **Estimate:** 0.5 pd
  - **Owner:** Jordi and Raúl
  - **Depends on:** 1.6, 1.11
  - **Files:** APPROACH.md, DEVELOPING.md, AGENTS.md, .agents/skills/possession-pipeline/SKILL.md, tests/compliance/test_docs.py
  - **Requirements:** Technical document matches the repository
  - **Verification:** `pytest tests/compliance/test_docs.py`; maintainer sign-off against the compliance log
  - **Done when:** Every compliance statement maps to the log and no public-window score is presented as a benchmark

- [ ] 1.14 Produce the G1 validated fallback
  - **Objective:** Generate a compliant fallback from a clean clone.
  - **Priority:** P0
  - **Estimate:** 0.25 pd
  - **Owner:** Jordi (human-local)
  - **Depends on:** 1.3, 1.4, 1.6, 1.10, 1.11, 1.12, 1.13
  - **Files:** docs/pulse/release-log.md, tests/compliance/test_release_log.py
  - **Requirements:** Deterministic output, Contract verification before success
  - **Verification:** human-local: two clean runs, equal SHA-256, official validator passes; `pytest tests/compliance/test_release_log.py`
  - **Done when:** The tag, hash and validator result are recorded, with no labels committed

## 2. P1: Core inference and validation

- [ ] 2.1 Create the dataset register and acquisition script
  - **Objective:** Register public games; fetch them into an ignored path.
  - **Priority:** P1
  - **Estimate:** 0.5 pd
  - **Owner:** Third member
  - **Depends on:** 1.4
  - **Files:** validation/datasets.toml, validation/acquire.py, tests/validation/test_register.py
  - **Requirements:** Authorised dataset register, Provided game excluded from selection
  - **Verification:** `pytest tests/validation/test_register.py`
  - **Done when:** Unregistered and competition datasets are refused and no data is tracked

- [ ] 2.2 Write adapters for public games
  - **Objective:** Convert Metrica samples first, then IDSSE if time allows.
  - **Priority:** P1
  - **Estimate:** 1.5 pd
  - **Owner:** Third member
  - **Depends on:** 1.7, 2.1
  - **Files:** validation/adapters/metrica.py, validation/adapters/idsse.py, tests/validation/test_adapters.py, tests/validation/fixtures/
  - **Requirements:** Adapters target the internal contract
  - **Verification:** `pytest tests/validation/test_adapters.py` on small team-written fixtures
  - **Done when:** At least the Metrica games pass contract validation with a quality report, or IDSSE is recorded as dropped

- [ ] 2.3 Build versioned reference labels
  - **Objective:** Derive H, A, D and ambiguity masks from events of other games, in at least two variants.
  - **Priority:** P1
  - **Estimate:** 1.5 pd
  - **Owner:** Third member
  - **Depends on:** 2.2
  - **Files:** validation/references.py, tests/validation/test_references.py
  - **Requirements:** Reference labels declare their uncertainty
  - **Verification:** `pytest tests/validation/test_references.py`
  - **Done when:** Rules are documented and sensitivity between variants is reported

- [ ] 2.4 Implement the corruption suite
  - **Objective:** Seeded dropout, tracklet, team, noise and tag corruption.
  - **Priority:** P1
  - **Estimate:** 1 pd
  - **Owner:** Third member
  - **Depends on:** 2.2
  - **Files:** validation/corruptions.py, tests/validation/test_corruptions.py
  - **Requirements:** Corruption suite
  - **Verification:** `pytest tests/validation/test_corruptions.py`
  - **Done when:** Same seed gives the same data, and zero strength equals adapter output

- [ ] 2.5 Implement the benchmark and freeze the suite
  - **Objective:** Run candidates with official metrics, confidence intervals and claim levels; pre-declare suite and margin.
  - **Priority:** P1
  - **Estimate:** 1 pd
  - **Owner:** Third member, with Raúl
  - **Depends on:** 2.3, 2.4
  - **Files:** validation/benchmark.py, validation/suite.toml, tests/validation/test_benchmark.py
  - **Requirements:** Statistical comparison, Claim levels are separate, Selection rule, Provided game excluded from selection
  - **Verification:** `pytest tests/validation/test_benchmark.py`; `python -m validation.benchmark --suite smoke`
  - **Done when:** The report states levels, intervals and the unknown private score, and the suite hash is recorded before candidate results exist

- [ ] 2.6 Move stoppage logic into the single dead-ball owner
  - **Objective:** Absorb phases 2 and 6 and the tagging parser's stoppage logic, with HARD and SOFT levels.
  - **Priority:** P1
  - **Estimate:** 2 pd
  - **Owner:** Jordi
  - **Depends on:** 1.10
  - **Files:** pipeline/dead_ball.py, pipeline/tagging.py, strategies/football_engine.py, tests/pipeline/test_dead_ball.py
  - **Requirements:** Single owner of stoppage decisions, Graded evidence strength, Ball absence is not a stoppage, Stoppage types without fixed sides, Restart resolution, Short unverified stoppages do not split possessions, Team references come from metadata, Inference works without tags
  - **Verification:** `pytest tests/pipeline/test_dead_ball.py`; human-local differing-frame count
  - **Done when:** Decoders contain no stoppage rule and every stoppage type has a synthetic scenario

- [ ] 2.7 Extract team evidence
  - **Objective:** Vectorised four-channel evidence and touch and contested signals.
  - **Priority:** P1
  - **Estimate:** 1.5 pd
  - **Owner:** Jordi
  - **Depends on:** 1.10
  - **Files:** pipeline/evidence.py, strategies/football_engine.py, tests/pipeline/test_evidence.py
  - **Requirements:** Four-channel frame evidence, Control features beyond proximity, Contested balls are distinguishable, Scores are not probabilities unless calibrated
  - **Verification:** `pytest tests/pipeline/test_evidence.py`
  - **Done when:** Bystander, touch, contested and missing-ball scenarios pass

- [ ] 2.8 Refactor the FSM behind the decoder interface
  - **Objective:** Add `TemporalDecoder`, per-half decoding, named switchable rules and shared boundary localisation.
  - **Priority:** P1
  - **Estimate:** 2 pd
  - **Owner:** Jordi, with Raúl
  - **Depends on:** 2.6, 2.7
  - **Files:** pipeline/temporal/__init__.py, pipeline/temporal/fsm.py, pipeline/temporal/boundaries.py, strategies/football_engine.py, config/pulse.toml, tests/pipeline/test_fsm.py
  - **Requirements:** Common decoder interface, Decoding is independent per half, Absent evidence is neutral, Spell integrity, Boundary localisation, Stoppage integration, Offline use of context
  - **Verification:** `pytest tests/pipeline/test_fsm.py tests/synthetic`
  - **Done when:** Each rule has a flag and id, and all spell scenarios pass with the FSM

- [ ] 2.9 Run rule ablations and decide class-B rules
  - **Objective:** Keep, change or remove rules on evidence.
  - **Priority:** P1
  - **Estimate:** 1 pd
  - **Owner:** Third member and Jordi
  - **Depends on:** 2.5, 2.8, 1.12
  - **Files:** docs/pulse/rule-register.toml, docs/pulse/decisions.md, tests/compliance/test_rule_register.py
  - **Requirements:** Component ablation, Rule provenance register
  - **Verification:** `python -m validation.benchmark --suite external --ablate-rules`; `pytest tests/compliance/test_rule_register.py`
  - **Done when:** Every class-B rule has a recorded decision consistent with any organiser answer

- [ ] 2.10 Implement the Viterbi challenger
  - **Objective:** First-order decoder with neutral missing evidence and hard stoppages.
  - **Priority:** P1
  - **Estimate:** 1.5 pd
  - **Owner:** Third member
  - **Depends on:** 2.8
  - **Files:** pipeline/temporal/viterbi.py, tests/pipeline/test_viterbi.py
  - **Requirements:** Common decoder interface, Absent evidence is neutral, Spell integrity, Offline use of context
  - **Verification:** `pytest tests/pipeline/test_viterbi.py`
  - **Done when:** Spell scenarios run on the challenger, with any failures listed for the decision

- [ ] 2.11 Decide the decoder (gate G2)
  - **Objective:** Apply the selection rule to FSM and Viterbi.
  - **Priority:** P1
  - **Estimate:** 0.5 pd
  - **Owner:** All
  - **Depends on:** 2.9, 2.10
  - **Files:** docs/pulse/decisions.md, config/pulse.toml, tests/validation/test_decision_record.py
  - **Requirements:** Evidence-based decoder selection, Selection rule
  - **Verification:** `python -m validation.benchmark --suite external`; `pytest tests/validation/test_decision_record.py`
  - **Done when:** The decision, suite hash and results are recorded, and the default follows the rule

- [ ] 2.12 Extend ball state estimation and test adoption
  - **Objective:** Add states, plausibility limits and uncertainty, disabled by default.
  - **Priority:** P1
  - **Estimate:** 1 pd
  - **Owner:** Raúl
  - **Depends on:** 1.7, 2.5
  - **Files:** pipeline/ball_reconstruction.py, config/pulse.toml, docs/pulse/decisions.md, tests/pipeline/test_ball_state.py
  - **Requirements:** Ball state classification, Conservative gap filling, Uncertainty grows with absence, Estimates cannot create hard facts, Evidence-gated adoption
  - **Verification:** `pytest tests/pipeline/test_ball_state.py`; ablation in `validation.benchmark`
  - **Done when:** All gap scenarios pass and the adoption decision is recorded, including rejection

- [ ] 2.13 Implement the abstention policy and uncertainty records
  - **Objective:** Prove the X policy with the official functions and add uncertainty causes.
  - **Priority:** P1
  - **Estimate:** 0.5 pd
  - **Owner:** Raúl
  - **Depends on:** 2.8
  - **Files:** pipeline/temporal/uncertainty.py, pipeline/submission.py, tests/pipeline/test_abstention.py
  - **Requirements:** Abstention policy derived from the scorer, Uncertainty is reported outside the labels
  - **Verification:** `pytest tests/pipeline/test_abstention.py`, importing `evaluation/possession_metrics.py` read-only
  - **Done when:** The dominance test passes and graded frames contain no X

- [ ] 2.14 Prepare and rehearse the release
  - **Objective:** Run the final checklist, public-repository audit and rehearsal.
  - **Priority:** P1
  - **Estimate:** 1 pd
  - **Owner:** All (human-local)
  - **Depends on:** 2.11, 2.12, 2.13
  - **Files:** docs/pulse/release-checklist.md, docs/pulse/release-log.md, APPROACH.md, tests/compliance/test_release_log.py
  - **Requirements:** Compliance questions are escalated and logged, Technical document matches the repository, Single submission entrypoint, Deterministic output
  - **Verification:** human-local clean-clone regeneration on the declared platform; official validator; `pytest tests/compliance`
  - **Done when:** Blocking questions are closed, the file is regenerated with an identical hash, and a human holds the correctly named deliverables

## 3. P2: Optional, only if P1 is on schedule

- [ ] 3.1 Normalise tag strength classes and simulate tag noise
  - **Objective:** Versioned class mapping and any additional fusion, under gated use.
  - **Priority:** P2
  - **Estimate:** 1 pd
  - **Owner:** Jordi
  - **Depends on:** 2.5, 2.6
  - **Files:** pipeline/tagging.py, config/pulse.toml, docs/pulse/decisions.md, tests/pipeline/test_tagging.py
  - **Requirements:** Tags are evidence, not truth, Evidence strength classes, Phase team tags are interval context, Missing, ambiguous and contradictory tags, Fusion benefit is not assumed
  - **Verification:** `pytest tests/pipeline/test_tagging.py`
  - **Done when:** Tag scenarios pass and extra fusion is adopted or recorded as not adopted

- [ ] 3.2 Build read-only diagnostics
  - **Objective:** Decision traces, suspicion reports and a static local HTML view, on top of the SRT tool.
  - **Priority:** P2
  - **Estimate:** 1.5 pd
  - **Owner:** Raúl
  - **Depends on:** 2.8
  - **Files:** tools/pulse_diagnostics.py, tools/generate_subtitles.py, tests/tools/test_diagnostics.py
  - **Requirements:** Decision traces, Suspicion reports, Read-only tooling, Diagnostics stay local
  - **Verification:** `pytest tests/tools/test_diagnostics.py`
  - **Done when:** Synthetic demo works, public-GT overlay is gone, and no input path can store labels

- [ ] 3.3 Add A/B comparison
  - **Objective:** Compare two runs with no ground truth.
  - **Priority:** P2
  - **Estimate:** 0.5 pd
  - **Owner:** Raúl
  - **Depends on:** 3.2
  - **Files:** tools/pulse_diagnostics.py, tests/tools/test_diagnostics.py
  - **Requirements:** A/B comparison without ground truth
  - **Verification:** `pytest tests/tools/test_diagnostics.py`
  - **Done when:** Differing intervals are listed with evidence and no score

- [ ] 3.4 Measure calibration on external games
  - **Objective:** Reliability curves, or a statement that uncertainty is uncalibrated.
  - **Priority:** P2
  - **Estimate:** 0.5 pd
  - **Owner:** Third member
  - **Depends on:** 2.13
  - **Files:** validation/calibration.py, docs/pulse/decisions.md, tests/validation/test_calibration.py
  - **Requirements:** Uncertainty is reported outside the labels, Scores are not probabilities unless calibrated
  - **Verification:** `pytest tests/validation/test_calibration.py`
  - **Done when:** A reliability report exists, or the outputs stay labelled as uncalibrated

- [ ] 3.5 Optimise measured hot spots
  - **Objective:** Vectorise only what profiling shows to matter.
  - **Priority:** P2
  - **Estimate:** 0.5 pd
  - **Owner:** Raúl
  - **Depends on:** 2.8
  - **Files:** pipeline/evidence.py, pipeline/temporal/fsm.py, tests/submission/test_performance.py
  - **Requirements:** Resource budget
  - **Verification:** `pytest tests/submission/test_performance.py`
  - **Done when:** The synthetic full-length run meets budgets with unchanged output hash, or no change was needed

## 4. P3: After phase 1

Not authorised for implementation under this change. Each item needs its own OpenSpec change:
video ball detection with Supervision, video-based recovery, broadcast and tactical synchronisation,
HSMM, Kalman smoothing, 3D ball, models trained on larger datasets, product dashboard, production infrastructure.

- [ ] 4.1 Close the change and hand over deferred work
  - **Objective:** Archive this change and list deferred items with their decisions.
  - **Priority:** P3
  - **Estimate:** 0.25 pd
  - **Owner:** Raúl
  - **Depends on:** 2.14
  - **Files:** docs/pulse/decisions.md, tests/compliance/test_rule_register.py
  - **Requirements:** Rule provenance register, Claim levels are separate
  - **Verification:** `openspec validate --all --strict --no-interactive`; governance checker with `--change design-pulse-possession-engine`
  - **Done when:** `verification.md` is COMPLETE, the change is archived and deferred items are listed as unapproved
