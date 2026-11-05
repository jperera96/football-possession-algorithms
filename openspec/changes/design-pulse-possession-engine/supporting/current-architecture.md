# Current architecture: evidence matrix

Baseline: `origin/main` at `54998ee` (2026-11-02). The audit commit `5e094e2` is 20 commits behind it.

**Method.** Reading of source and Git metadata, plus a static AST count. No code was run on match
data. Not read: `data/`, `tests/baseline/football_engine_segments.json`, `evaluation/results/*.csv`,
`experiments/history.jsonl`, `experiments/EXPERIMENT_LOG.md`. Numbers in `tests/test_golden_spells.py`
were masked before reading. Frame numbers from commit subjects are deliberately not repeated here.

**Evidence labels.** CONFIRMED: seen directly in code or history. INFERRED: a reasoned conclusion from
confirmed facts. UNVERIFIED: cannot be checked without running on data, or claimed only in documentation.

## What changed since the audit

| Audit topic | Status at `54998ee` |
|---|---|
| Engine | Grew and split into seven methods (`59a8a2d`), still one class. New rules: continuity filter, in-pitch free kicks, corner envelopes, goalkeeper continuity |
| Match constants | Still present, with more of them. Static count in `football_engine.py`: first-half end literal 8 times, second-half start 4, slot numbers 23 and 45 in 7 and 9 places (45 also occurs as a non-slot value), halfway literal 6 |
| New tools | `tools/regression_check.py`, `tests/test_golden_spells.py`, `tests/baseline/football_engine_segments.json` |
| CI | Adds a golden step that skips itself without data |
| Cache, `--test-all`, external validation | Unchanged |

## Component matrix

| Component | Responsibility | State | Problems | Decision | Evidence |
|---|---|---|---|---|---|
| `strategies/football_engine.py` | Production labels | Works as code; 1,405 lines, 708 numeric literals | Class A constants; rules act on labels and on each other; order dependence | REFACTOR by stage; frozen as reference until G2 | CONFIRMED |
| `_run_base_fsm` | Inertia and barrier | Clear, compact | Window lag needs later backtracking rules | KEEP, move to `pipeline/temporal/fsm.py` | CONFIRMED; lag INFERRED |
| `_refine_smart_tagging_set_pieces` | Tag refinement | Works as code | Overlaps `dead_ball.py`; magic windows | REFACTOR into `dead_ball` | CONFIRMED |
| `_compute_spatial_evidence` | Nearest player, windows | Works as code | Nearest-only; per-frame loop; slot-swap heuristic uses slots and frame constants | REFACTOR into `evidence` | CONFIRMED |
| `_resolve_physical_turnovers` | Post-rules on labels | 547 lines, 205 branch or loop nodes | Hard to test; class A and B mix | REFACTOR into named rules, then ablate | CONFIRMED |
| `_resolve_stoppage_envelopes` | Untagged free kicks, corners | Works as code | Frame guards; side rules; duplicates stoppage ownership | REFACTOR into `dead_ball` | CONFIRMED |
| `_apply_continuity_filter` | Flicker removal | Simple | Duplicated `return` | KEEP, ablate | CONFIRMED |
| `_compute_kinematics` | Speeds | Works | Undefined speed becomes 0.0 | REFACTOR into `BallTrack` | CONFIRMED |
| `strategies/base.py` | `TrackingContext`, `BaseStrategy` | Useful | Mixes raw data and decisions; dict-typed tags | EXTEND with adapter | CONFIRMED |
| `pipeline/dead_ball.py` | Stoppages, tag parser | Partly reusable | Fixed frame tuples; club names in parsing; 105.3 x 68 literals | REFACTOR as single owner | CONFIRMED |
| `pipeline/evidence.py` | Single-frame evidence | Small | Not used by production engine; per-frame | EXTEND, vectorise | CONFIRMED |
| `pipeline/ball_reconstruction.py` | Linear interpolation | Small and tested by use elsewhere | Not used by production engine; docstring promises carrier tracking that is absent | EXTEND; EXPERIMENTAL | CONFIRMED |
| `pipeline/state_machine.py` | Lookahead FSM | Older path | Second state machine | DEPRECATE; compare lookahead as option | CONFIRMED |
| `pipeline/runner.py` | Older entrypoint | Different semantics | Second parser; kickoff anchors; `stoppages` undefined if tag file is absent; pitch-bounds D from interpolated ball | DEPRECATE | CONFIRMED |
| `strategies/hmm_viterbi.py` | Viterbi | Prototype | Arbitrary scores; no durations; interpolated input; dead-mask dependency; per-frame Python | REPLACE by gated challenger | CONFIRMED |
| `strategies/fsm_*` | Experiments | Available | Not production | KEEP as experiments, then DEPRECATE if unused | CONFIRMED |
| `strategies/baseline_window.py` | Baseline | Useful comparator | None relevant | KEEP | CONFIRMED |
| `games.py` | Published facts and paths | Good, documented | None; team, side and slot facts must not enter it | EXTEND with `GameConfig` | CONFIRMED |
| `run_experiment.py` | Loading, scoring, logging | Used for production | Implicit cache; second parser; scores automatically on public GT and logs it; `--test-all` cannot fail | REFACTOR | CONFIRMED |
| `tools/agent_eval.py` | Compact scoring | Reads a submission | Encourages repeated public scoring | KEEP for format checks only; flagged | INFERRED |
| `tools/regression_check.py` | Metric floor, diff | Active gate | Public metric floor; tracked full-match label snapshot; `--update` workflow | REFACTOR to local-only comparison | CONFIRMED |
| `tools/sweep_hysteresis.py` | Parameter sweep | Script | Sweeps against public GT | REPLACE by external benchmark | CONFIRMED |
| `tools/generate_subtitles.py` | SRT overlay | Useful | Match constants; public-GT overlay; requires match data; output in `data/` | EXTEND into diagnostics | CONFIRMED |
| `tests/test_golden_spells.py` | Frame expectations | Skips without data | Human-derived expectations on the provided game | REMOVE from tree; keep contract invariants as synthetic tests | CONFIRMED |
| `test_synthetic` methods | Self-checks | Pass by design | Engine uses 100 frames, most later phases need more | REPLACE by generator | CONFIRMED |
| `.github/workflows/ci.yml` | CI | Runs | No gate can detect engine failure; unpinned actions | REFACTOR | CONFIRMED |
| `requirements.txt` | Dependencies | Two lines | Unpinned | EXTEND with lockfile | CONFIRMED |
| `evaluation/*`, `starter/*` | Official | Do not modify | None | KEEP untouched | CONFIRMED |
| `APPROACH.md` | Technical document | Polished | Compliance and reproduction statements conflict with code and history | Correct under task 1.13 | CONFIRMED text; INFERRED conflict |
| Private-match score | Unknown | No value exists | No score of any engine is known | Never estimate | UNVERIFIED |
| "~6 seconds" run time | `APPROACH.md` claim | Not measured here | May depend on the cache | Measure locally | UNVERIFIED |

## Compliance inventory

Statements of fact about the repository; they are not findings of intent. The rule text decides what
must change, and organisers decide doubtful cases.

| ID | Item | Rule | Assessment | Action |
|---|---|---|---|---|
| C1 | Frame literals in inference | `RULES.md` 1 | CONFIRMED present; graded boundaries are published, so their *location* is the issue | Move to config; infer the rest |
| C2 | Kicking teams, side per half, slot numbers | `RULES.md` 1 | CONFIRMED present | Infer |
| C3 | Frame-window expectations from watching the video | `RULES.md` 1 ("No hand labels ... not to validate one") | CONFIRMED; direct conflict with the text as read | Remove from tree, log, ask |
| C4 | Commit series fixing specific frames across the match, outside the public window | `RULES.md` 1 ("rules and constants tied to specific frames") | CONFIRMED pattern; whether each resulting general rule breaches the text is a judgement | Class-B review, ask |
| C5 | Public metric floors and sweep | `RULES.md` 2, `EVALUATION.md` | CONFIRMED | Remove |
| C6 | Tracked full-match label snapshot | `.gitignore` policy, `RULES.md` data terms | CONFIRMED tracked; content not read; publication impact unclear | Remove from tree, ask whether history matters |
| C7 | `APPROACH.md` statements on public GT use | `SUBMISSION.md`, `RULES.md` | INFERRED mismatch | Correct, disclose |
| C8 | `AGENTS.md` on `main` instructs adding golden cases | Governance | CONFIRMED | Change |

Watching the video to debug and design features is allowed by `RULES.md`. The boundary concerns what
was turned into labels, corrections, or rules and constants tied to frames. That is why C4 needs a
decision rather than an automatic deletion.

## Engine rule classes

**Class A:** contains or depends on a match constant, so it must change. **Class B:** general logic,
but with thresholds or structure derived from observed cases on the provided game, so it needs
external evidence, or a ruling. **Class C:** physical or structural logic with no case dependence
known. Classes are initial, from reading code and commit subjects (INFERRED). Task 1.12 finalises them.

| Rule (engine step) | Class | Note |
|---|---|---|
| Goalkeeper slot disambiguation | A | Slots, halves, sides |
| Dynamic tracklet swap | A + B | Slots, half constant, case-derived thresholds |
| Kickoff arrival | A | Frames, kicking teams, sides |
| Half-dependent clearances (6) | A + B | Sides by frame |
| Two-player counter-pass (6b) | A + B | Sides by frame |
| Post-occlusion reception (6c) | B | |
| Bystander removal (6d) | B | |
| Contested duel rejection (6e) | A + B | Sides by frame |
| Pre-dead split (7) | B | |
| Restart backtracking (9) | B | |
| Goalkeeper catch continuity (10) | A + B | Frames, box literals, sides |
| In-pitch free kick (11) | A + B | Frame guards, slots |
| Corner envelope (11b) | A + B | Sides by frame |
| Set-piece bridge, pre-roll, goal build-up | B | |
| Throw-in restart verification | C | Team names in the parser are class A |
| Deflection filter (5) | C | Parameter unverified |
| Unverified D bridging (8) | C | Parameter unverified |
| Base FSM, windows, barrier | C | Parameters unverified |
| Flicker filter (12) | C | Parameters unverified |

## Other technical debt

- Literal `25.0`, `105`, `68.0` where config exists; `52.5` is not half of the configured 105.3.
- `min_dist_*` sentinel 99.0 in place of NaN.
- Stage order dependence: later rules reread labels edited by earlier rules.
- `build_match_context` constructs decisions (dead mask, restarts) before the strategy runs.
- Interpolated balls can produce out-of-bounds stoppages in `pipeline/runner.py`.
