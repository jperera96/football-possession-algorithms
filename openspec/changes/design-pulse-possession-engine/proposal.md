# Proposal

> Status: **proposed, not approved.** This file becomes approved only when a human merges it into
> `main` through a specification PR. Code references are to `origin/main` at `54998ee`, which is 20
> commits ahead of this branch's base (`5e094e2` plus the governance bootstrap). The evidence
> labels CONFIRMED / INFERRED / UNVERIFIED are defined in `supporting/current-architecture.md`.

## Why

**Problem statement.** The team has a working heuristic engine, but it cannot currently be shown
to be a valid competition entry, and nobody can measure whether a change improves it.

1. **Compliance exposure (blocking).** The rules prohibit hand labels on the provided game "in any
   amount and for any purpose", including validation, and prohibit "rules and constants tied to
   specific frames of the game" (`RULES.md`). The repository contains human-derived expected labels
   for specific frames, match frame constants inside inference code, and a public-ground-truth
   metric floor used as a regression gate. See *Current Behavior*.
2. **No legitimate selection signal.** No benchmark exists outside the competition match. The only
   numbers in the repository come from the public 5 minutes, which `RULES.md` and `EVALUATION.md`
   exclude from tuning and selection, and which have no ranking value.
3. **Reproducibility gap.** `RULES.md` rule 3 requires the repository to regenerate the same file.
   Today two entrypoints run different algorithms, and the production path silently prefers a cache
   that no code in the repository writes.
4. **Ineffective quality gates.** The commands that look like tests cannot fail on the conditions
   that matter, and most engine phases are unreachable from its synthetic test.
5. **Unmaintainable growth.** One 1,405-line class holds 708 numeric literals, and each new case
   adds a rule. Without ablation evidence no rule can be retired.

**Motivation.** The deadline is 2026-11-17 (12 days from this proposal). There is no live
leaderboard, so the private score stays unknown until after submission. A disqualified or
unreproducible file scores nothing, whatever its accuracy. Validity therefore comes first, and
measurable improvement second.

## Current Behavior

Full matrix with evidence levels: `supporting/current-architecture.md`. Summary:

- **Production engine** (`strategies/football_engine.py`, CONFIRMED): seven-phase heuristic pipeline
  around an inertia FSM with windowed evidence and a turnover barrier (`_run_base_fsm`), plus
  post-processing rules. `_resolve_physical_turnovers` alone is 547 lines.
- **Match-specific constants in inference** (CONFIRMED): half boundaries, kickoff frames and kicking
  teams, attack direction per half, goalkeeper slots and a fixed halfway line appear as literals
  (`_resolve_slot_team`, `_resolve_physical_turnovers`, `_resolve_stoppage_envelopes`,
  `pipeline/dead_ball.py`, `pipeline/runner.py`, `run_experiment.py`, `tools/generate_subtitles.py`).
- **Human-derived frame expectations** (CONFIRMED): `tests/test_golden_spells.py` describes itself as
  "human-verified" observations from watching the tactical video, asserted over specific frames of
  the provided game. `AGENTS.md` on `main` instructs adding one case per fix. 20 commits between
  `5e094e2` and `54998ee` follow that loop; many subjects name specific frames.
- **Public metric gate and label snapshot** (CONFIRMED): `tools/regression_check.py` fails below a
  public-window `spellF1` / `macroF1` floor and diffs against a committed run-length encoding of the
  full-match labels (`tests/baseline/football_engine_segments.json`). `tools/sweep_hysteresis.py`
  sweeps parameters against the public ground truth. The content of the JSON file was deliberately
  not read for this proposal.
- **Technical document mismatch** (CONFIRMED that the text exists; INFERRED that it is inaccurate):
  `APPROACH.md` states that the public ground truth was used strictly as a sanity check. Commit
  history, `tools/regression_check.py` and `tools/sweep_hysteresis.py` do not support that statement
  as written.
- **Reproducibility** (CONFIRMED): `run_experiment.py:build_match_context` prefers
  `data/cache/tracking_context.npz`, and no repository code writes that file. `pipeline/runner.py`
  is a second entrypoint with a different FSM, interpolated ball input and a different output file.
  Dependencies are unpinned. The ATD parser is duplicated.
- **Tests** (CONFIRMED): `run_experiment.py --test-all` exits 0 even when a strategy fails.
  `FootballEngineStrategy.test_synthetic` uses 100 frames while most later phases require
  `n_frames > 100`. Golden tests skip themselves in CI.
- **Missing-value handling** (CONFIRMED): `_compute_kinematics` turns undefined ball speed into 0.0,
  so absence can read as a stationary ball.
- **Unused or weak components** (CONFIRMED): `pipeline/ball_reconstruction.py` is not used by the
  production engine. `hmm_viterbi.py` has uncalibrated scores, no duration model and per-frame Python
  evidence. `tools/generate_subtitles.py` can only run on the competition match.
- **Performance on the full private match**: UNVERIFIED. No full-match score exists for any engine.

## Desired Behavior

- One command regenerates the submission byte-for-byte from authorised inputs on a clean clone.
- Inference contains no constant, rule or test tied to a frame, spell, team, side or slot of the
  provided game. Mirroring the pitch or swapping team labels yields the mirrored or swapped result.
- Model and rule selection uses independent games and synthetic stress tests, reports uncertainty,
  and never uses the public 5 minutes or hand labels on the provided game.
- Observations, reconstructions, evidence, decoded states and exported labels are separate typed
  layers, with explicit missing values and provenance.
- All stoppage decisions have one owner. Smart Tagging is weighted evidence, never truth.
- A temporal decoder interface lets the refactored FSM and a Viterbi decoder compete under a
  pre-declared rule. The simpler decoder wins unless the evidence says otherwise.
- Diagnostics explain decisions and cannot store human labels or corrections.

## What Changes

This specification PR changes **planning artifacts only**. Once approved, later implementation PRs
will:

- **BREAKING** remove `tests/test_golden_spells.py` frame cases, the committed full-match label
  snapshot and public metric floors from all gates. History stays in Git and is logged, not rewritten.
- **BREAKING** replace `pipeline/runner.py` and the implicit cache path with one entrypoint,
  `make_submission.py`.
- Move official per-game facts to game configuration and infer direction, kicking team and tracklet
  team from tracking.
- Add typed contracts, a synthetic match generator and property tests.
- Add the external validation framework (`validation/`) for public games.
- Decompose `football_engine` behind stable stage interfaces, keeping behaviour unless a task says
  otherwise, then classify and ablate its rules.
- Add evidence, dead-ball, ball-state and decoder capabilities under gated adoption.
- Evolve subtitles into local, read-only diagnostics.

## Capabilities

### New Capabilities

- `competition-compliance`: prohibited inputs, constants, labels and claims, and how they are checked.
- `possession-data-contract`: indexing, units, missing values, tracklets, inferred match facts, data layers.
- `ball-state-estimation`: observed, interpolated, estimated and unknown ball states.
- `team-control-evidence`: per-frame H / A / none / insufficient evidence beyond nearest player.
- `dead-ball-detection`: single source of truth for stoppages and restarts.
- `smart-tagging-fusion`: Smart Tagging as weighted, optional evidence.
- `temporal-possession-inference`: decoders, segmentation, boundaries, uncertainty and abstention policy.
- `possession-diagnostics`: read-only decision traces, suspicion reports, A/B comparison.
- `external-validation`: datasets, reference labels, corruption, claim levels, selection rule.
- `submission-reproducibility`: entrypoint, determinism, cache, manifest, environment, quality gates.

Prediction confidence (module 7 of the brief) is part of `temporal-possession-inference` because
its only observable outputs are decoder uncertainty and the abstention policy.

### Modified Capabilities

None. `submission-contract` already states the file format, and `submission-reproducibility` relies
on it without changing it.

## Change Type

Type: algorithm

## Alternatives Considered

- **Keep adding rules to `football_engine`.** Rejected. It deepens the compliance exposure, and no
  evidence exists to justify or retire a rule.
- **Rewrite as a new engine.** Rejected. It discards the only working pipeline 12 days before the
  deadline and would have no better selection signal.
- **Replace the FSM with Viterbi or an HSMM now.** Rejected as a decision. Both become candidates
  behind one interface; the external benchmark decides.
- **Train a neural sequence model.** Rejected for phase 1. Reference labels would be few and
  approximate, and the domain gap to the competition tracking is large.
- **Ten separately delivered changes.** Rejected for review cost. One approved contract, delivered
  in staged PRs, fits the deadline better. If review of the whole contract would delay P0, see
  *Migration Strategy*.

## Out of Scope

- Any implementation in this PR, including algorithm, scorer, baseline or CI changes.
- Changes to `evaluation/` or `starter/baseline.py`.
- Video-based detection, broadcast synchronisation, 3D ball modelling, trained deep models, services,
  databases, containers or a product dashboard (P3 at the earliest, each with its own OpenSpec change).
- Rewriting Git history.
- Contacting organisers or changing GitHub settings. Both are human decisions.

## Affected Modules

Must agree with `affected_areas` in `.openspec.yaml`:

- Inference: `strategies/**`, `pipeline/**`, `games.py`, `run_experiment.py`, new `make_submission.py`, `config/**`.
- Validation: new `validation/**`; `tests/**` subfolders listed in `.openspec.yaml`, excluding `tests/governance/`.
- Tools: `tools/regression_check.py`, `tools/sweep_hysteresis.py`, `tools/generate_subtitles.py`,
  `tools/pre_commit.py`, new `tools/pulse_diagnostics.py`.
- Environment and CI: `pyproject.toml`, `uv.lock`, `requirements.txt`, `.github/workflows/ci.yml`.
- Documentation and agent guidance: `AGENTS.md`, `APPROACH.md`, `DEVELOPING.md`,
  `experiments/README.md`, `docs/pulse/**`, `.agents/skills/possession-pipeline/**`.

Protected and untouched: `evaluation/**`, `starter/**`, `tools/governance/**`, `tests/governance/**`,
`.github/workflows/governance.yml`, `openspec/schemas/**`.

## Expected Benefit

Certain once implemented, and checkable with tests: removal of the identified rule conflicts, a
byte-identical regeneration path, effective CI, and a selection method that does not touch the
provided game's labels. **No score improvement is claimed.** Removing match-specific logic may lower
performance on the competition match, and that effect cannot be estimated here.

## Risks

Full register: `design.md`, *Risks*.

- Organisers may rule that past work requires further remediation, or that rules derived from
  watching the video must go.
- Removing constants and class-B rules can reduce private-match accuracy, invisibly.
- Public games differ from competition tracking, so external results may not transfer.
- Event-derived reference labels are approximate, which can mislead selection.
- Review and approval time consumes the short schedule.
- Three people touching one engine creates merge conflicts.

## Rollback

Every implementation PR is revertible on its own. Until the decoder decision, the refactored FSM
stays the default. Gate G1 (`supporting/roadmap.md`) tags a validated fallback commit, from which a
valid file can always be regenerated. A later candidate is adopted only if it passes every gate.

## Evidence

- Direct reading of the source and history on `origin/main` at `54998ee`, plus a static count of
  literals and method sizes (`supporting/current-architecture.md`). No script that loads match data
  was run, and no private asset, prediction file or experiment log content was read.
- Official documentation: `RULES.md`, `FAQ.md`, `EVALUATION.md`, `SUBMISSION.md`, `DATA.md`.
- Scorer reading: `fill_abstentions` in `evaluation/possession_metrics.py` shows that `X` is
  forward-filled for temporal metrics and charged by macroF1.
- Public dataset metadata: see `supporting/external-validation-protocol.md`.
- Public 5-minute scores are not used as evidence anywhere in this change.

## Competition Constraints

- Labels produced by an algorithm only. No hand labels on the provided game, for any purpose.
- No full-match ground truth, or anything derived from it, and no human-produced data about the
  provided game from any source. Data about other games is allowed.
- Public 5 minutes for pipeline checking only.
- The repository must regenerate the same file, and must be public at submission.
- Everything used must be accessible to organisers and explained in the technical document.
- Match assets must not be redistributed, and must not reach third-party hosted LLMs.
- When a rule is unclear, ask organisers before building on it.

## Architectural Principles

In priority order: rule compliance, reproducibility, temporal correctness, reduced fragmentation,
reliable dead-ball detection, physical modelling of control, explicit uncertainty, generalisation,
testability, performance, simplicity, explainability. Technology is added only to solve a named
problem, and only with a validation path.

## Dependencies

- PR `jperera96/football-possession-algorithms#1` must merge first. This change is stacked on it.
- Human decisions D1 to D5 in `README.md`, and organiser answers where requested.
- No new runtime dependency in the core. See `supporting/technology-review.md`.

## Migration Strategy

Strangler approach. `football_engine` stays registered as the reference while stages move behind
contracts, with output-equivalence checks run locally by a human. Implementation branches start from
`main`, not from this stacked branch.

Fallback if full review would delay P0 past 2026-11-07: maintainers may ask for a reduced
specification PR containing only `competition-compliance`, `possession-data-contract`,
`submission-reproducibility` and the P0 tasks, and approve the rest later.

## Success Criteria

- Every P0 task is verified, and gate G1 yields a validated, reproducible fallback.
- Static compliance tests and mirror / swap property tests pass in CI.
- Two runs from clean clones produce identical hashes, as run by a human on the authorised data.
- The external benchmark runs in CI-sized form on synthetic data and in full on public games.
- The decoder decision and every class-B rule decision are recorded with their evidence.
- The technical document matches the repository and the compliance log.
- The submission is made by a human before the deadline, with `validate_submission.py` passing on
  the exact file.

## Algorithm Review

### Hypothesis

Possession is a persistent latent state observed through sparse, noisy evidence. Separating
evidence from temporal decoding, and treating absence as absence rather than as data, should yield
spells that generalise better than rules fitted to observed cases. This is a hypothesis to test,
not a finding.

### Evidence Beyond the Competition Match

Physics of ball and player motion, the IFAB Laws of the Game, the sequence-modelling literature, and
the official statement that per-frame decisions fragment possessions (`FAQ.md`, `EVALUATION.md`).
Empirical support must come from the public games in the external benchmark. None exists yet.

### Simpler Alternatives

The existing inertia FSM with windowed evidence is the default and stays so unless beaten. Simple
linear interpolation is preferred to a Kalman filter. A first-order Viterbi decoder with minimum
durations is preferred to an HSMM. Removing rules is preferred to adding them.

### Evaluation Methodology

The official `evaluation/possession_metrics.py`, used as a read-only library, on public games with
event-derived reference labels, under synthetic corruption, with leave-one-game-out analysis and
paired bootstrap intervals, spellF1 first. Full protocol in
`supporting/external-validation-protocol.md`.

### Ablation

Every engine rule and every new component has an on/off flag exercised by the benchmark. Components
that show no benefit under the selection rule are removed or stay disabled.

### Failure Modes

Long ball absence, tracklet swaps and duplicates, wrong team on a tracklet, aerial balls projected
onto the pitch, crowded scrambles, unlabelled stoppages, false Smart Tagging events, and short genuine
possessions removed by smoothing. Each has a synthetic scenario in the specs or tasks.

### Generalization

Nothing may depend on BAR-ATH frames, teams, sides or slots. Mirror and team-swap properties make
this testable, and running on other games proves the pipeline has no hidden dependency on the match.

### Reproducibility

A single deterministic entrypoint, pinned environment, versioned parameters, a hash-keyed optional
cache proven equivalent to no cache, and a manifest of inputs and outputs. Parameter provenance is
recorded per parameter.

### Complexity

Maintenance cost falls if class-B rules are retired. The Viterbi candidate adds a small numerical
module. An HSMM is implemented only if the benchmark shows a duration-specific failure that the
simpler decoder cannot fix.

### Falsification

A component is rejected if it fails the selection rule, if it breaks a property test, or if a
mirror or swap test exposes a hidden match dependency. PULSE decoding as a whole is rejected for
phase 1 if it does not beat the refactored FSM by the rule's margin by 2026-11-14.

### Expected spellF1 Impact

Unknown. Expected direction on public games: fewer false splits. On the competition match: unknown,
possibly negative after removing match-specific logic. Only external results will be reported, and
no competition score will be estimated.

### Why This Is Not a Match-Specific Patch

Its purpose is to remove such patches. Requirements contain no competition frame, spell, team, side
or slot. Competition facts allowed in configuration are limited to those the organisers publish,
such as frame counts and graded intervals.
