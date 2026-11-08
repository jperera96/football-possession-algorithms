# Proposal

> Status: **proposed, not approved.** It is approved only when a human merges it into `main` through a
> specification PR. This change replaces the earlier draft `design-pulse-possession-engine`, which was
> never approved. Code references are to `origin/main` at `54998ee`, unchanged on 2026-11-08.

## Why

The team's goal is for the engine's quality to hold over the whole match, and not only over the 5
public minutes, where it scores spellF1 0.9375 and macroF1 0.9732.

That number cannot show whether it does:

- **It is in-sample.** `experiments/history.jsonl` records 44 runs, all scored on the public window,
  and the engine was developed by comparing each version with that score. Over two days it rose from
  0.28 to 0.9375. `EVALUATION.md` shows why this misleads: the window that wins on the public 5
  minutes loses on the full match.
- **It is saturated.** 0.9375 means 15 of 17 public possessions matched and no extra predictions. The
  last 21 runs score exactly the same, so the window no longer measures any change.
- **It is imprecise.** With 17 possessions, the 95% interval for recall is about 0.66 to 0.97. The
  window covers 4.7% of graded time, and all of it at the start of the first half.
- **Nothing else can measure it.** There is no full-match ground truth and no leaderboard. Checking the
  rest of the match by watching the video is hand labelling, which `RULES.md` prohibits "in any amount
  and for any purpose", including validation.

So holding the score on the full match has to come from **generalisation**: an engine with no
knowledge specific to this match, measured on other games, robust to the data failures the
competition data has, and checked on the full match without labels.

There is also a practical blocker. The engine hardcodes this match's frames, kicking teams, sides and
goalkeeper slots, so it cannot run on any other game. Measuring it elsewhere is impossible until that
changes.

## Current Behavior

Evidence and labels in `supporting/current-architecture.md` and `supporting/experiments-analysis.md`.

- `strategies/football_engine.py`: seven phases, 1,405 lines, 708 numeric literals. Literals include
  half boundaries, kickoff frames and teams, attack direction per half, goalkeeper slots 23 and 45, and
  a fixed halfway line (CONFIRMED).
- Development loop (CONFIRMED from history): score on the public window, and add golden cases from
  watching the tactical video. `tests/test_golden_spells.py` describes its cases as "human-verified".
  `tools/regression_check.py` enforces a public-metric floor and diffs a tracked full-match label snapshot.
- No external or synthetic benchmark exists. `run_experiment.py --test-all` exits 0 on failure. The
  production path silently uses `data/cache/tracking_context.npz`, which no code writes (CONFIRMED).
- `BaselineWindowStrategy` scores 0.2900 on the public window while the official `baseline_smooth50`
  file scores 0.3256 (CONFIRMED numbers; cause UNVERIFIED), so in-repo baselines do not reproduce the
  official one exactly.
- Full-match performance of any version: UNVERIFIED and unknowable before submission.

## Desired Behavior

- The engine runs unchanged on any game in the internal format. It holds no match-specific constant,
  and gives mirrored or swapped results for mirrored or swapped inputs.
- Each engine rule can be switched off, has a register entry, and is kept only on evidence from other
  games or synthetic tests.
- The team has an out-of-sample measure: spellF1 on public games of other matches, with uncertainty,
  under realistic corruption, against the baseline.
- A label-free audit of the full competition match, run locally by a human, shows whether behaviour
  inside the public window resembles behaviour in the rest of the match.
- One command regenerates the submission identically. Gates and tests fail when something is wrong.

## What Changes

Planning only in this PR. Once approved, implementation PRs will:

- Move published facts (frame count, graded intervals, pitch) to configuration, and infer attack
  direction, kicking team and tracklet team from tracking.
- **BREAKING** remove frame-window golden tests, the tracked label snapshot, public-metric floors and the
  public sweep from the tree and from gates, with Git history kept and a compliance log.
- Give every engine rule an identifier and a switch, and add a rule register.
- Add a small external benchmark (`validation/`): Metrica sample games, event-derived references,
  seeded corruption, official metrics, a frozen selection rule.
- Add `tools/match_audit.py`, a human-run, aggregate-only, label-free audit of the full match.
- Prune or change rules on ablation evidence, then improve the engine on failures seen in other games.
- Add a single reproducible entrypoint, a pinned environment and tests that can fail.

## Capabilities

### New Capabilities

- `competition-compliance`: what the repository must never contain or claim.
- `engine-generalization`: game-independent engine behaviour, rule switches and register.
- `external-validation`: out-of-sample measurement and the selection rule.
- `label-free-match-audit`: aggregate diagnostics on the competition match without labels.
- `submission-reproducibility`: entrypoint, determinism, environment and gates.

### Modified Capabilities

None.

## Change Type

Type: algorithm

## Alternatives Considered

- **Keep improving against the public window and video review.** Rejected. It cannot measure the full
  match, the window is saturated, and the rules prohibit it.
- **Hold 0.9375 as a regression floor.** Rejected. That is selection on the public window, and it would
  block changes that generalise better.
- **Rewrite with a probabilistic decoder (earlier PULSE draft).** Deferred. Too much for nine days, and
  the external benchmark must exist before any engine can be compared.
- **Estimate full-match quality from statistics of possessions in football.** Used only as a sanity
  signal inside the audit, never as a target.

## Out of Scope

Implementation in this PR; `evaluation/**` and `starter/**`; new runtime dependencies; video
processing; Viterbi or HSMM decoders and ball reconstruction beyond optional P2 experiments; history
rewriting; contacting organisers or changing GitHub settings.

## Affected Modules

`strategies/**`, `pipeline/**`, `games.py`, `run_experiment.py`, new `make_submission.py`, `config/**`,
new `validation/**`, `tools/match_audit.py`, `tools/regression_check.py`, `tools/sweep_hysteresis.py`,
`tools/agent_eval.py`, `tools/generate_subtitles.py`, `tools/pre_commit.py`, test folders listed in
`.openspec.yaml`, `pyproject.toml`, `uv.lock`, `requirements.txt`, `.github/workflows/ci.yml`,
`AGENTS.md`, `APPROACH.md`, `DEVELOPING.md`, `experiments/README.md`, `docs/engine/**`,
`.agents/skills/possession-pipeline/**`. Untouched: `evaluation/**`, `starter/**`, governance files.

## Expected Benefit

- The first out-of-sample measurement the project has ever had.
- An engine that can run on other games.
- Rules kept for evidence rather than for a single frame.
- A valid, reproducible entry.

**No score is promised.** The public-window score may fall when match-specific logic goes. That fall
reveals in-sample optimism and is not by itself a regression.

## Risks

- Removing constants and patch-like rules may lower the competition score.
- Metrica sample games differ from the competition tracking, so external results may not transfer.
- Event-derived references are approximate.
- Approval may come late, leaving little time.
- The team may disagree with removing the golden tests; that decision belongs with them and the organisers.

## Rollback

Each implementation PR can be reverted alone. Gate G1 tags a compliant fallback, from which a valid
file can always be regenerated. Rules move behind switches before any removal, so a rule can be
restored by configuration.

## Evidence

- Reading of source and history at `54998ee`, including a static literal count.
- `experiments/history.jsonl` and `EXPERIMENT_LOG.md`, read with frame numbers masked in the JSON, see
  `supporting/experiments-analysis.md`.
- `RULES.md`, `FAQ.md`, `EVALUATION.md`, `DATA.md`, `SUBMISSION.md`.
- Public metadata of external datasets, in `supporting/validation-protocol.md`.
- No code was run on match data while preparing this proposal.

## Success Criteria

- The generalised engine runs unchanged on the competition match and on at least two external games.
- Mirror, team-swap and slot-permutation tests pass.
- External spellF1 for the generalised engine and for the baseline is reported per game with 95%
  intervals, clean and under corruption.
- Every rule has a recorded keep, change or remove decision backed by evidence.
- The label-free audit has been run by a human and its aggregate report reviewed.
- Two clean-clone runs produce the same hash, the official validator passes, and the technical
  document matches the repository.

## Algorithm Review

### Hypothesis

Rules fitted to observed cases of one match carry a share of match-specific behaviour. An engine
restricted to game-independent logic, kept only where external evidence supports it, keeps more of its
quality outside the public window than the current version would.

### Evidence Beyond the Competition Match

Physics and IFAB Laws for every remaining rule; public games of other matches with events for
measurement; `EVALUATION.md` for the public-window trap. No external result exists yet; producing one
is the first goal.

### Simpler Alternatives

Keep the current engine and only replace constants. That is task group 1 and also the fallback.
Further work happens only if it beats the fallback externally.

### Evaluation Methodology

Official `evaluation/possession_metrics.py` used read-only, on Metrica sample games (IDSSE optional),
with two event-derived reference variants, seeded corruption, per-game results and paired bootstrap.
Never the public window or the competition match for selection.

### Ablation

Every rule has a switch. Each is turned off in turn on the external suite, and the effect is reported
with its interval.

### Failure Modes

Ball absence near duels; tracklet swaps; wrong team on a tracklet, especially goalkeepers; aerial balls;
untagged stoppages; restarts; deflections; short real possessions removed by filters.

### Generalization

Validated directly: the engine must run on other games, and mirror, swap and permutation tests must
pass. The label-free audit compares behaviour inside and outside the public window.

### Reproducibility

Single entrypoint, pinned environment, versioned rule switches and parameters, optional cache proven
equal to no cache, manifest with hashes.

### Complexity

Lower than today: rules gain switches and identifiers, and some are expected to go. No new runtime
dependency.

### Falsification

A rule or change is rejected if it fails the selection rule externally or breaks an equivariance test.
If generalisation work loses to the constant-replaced fallback on the external suite, the fallback ships.

### Expected spellF1 Impact

Unknown on the competition match. Public-window spellF1 may go down, and that is acceptable. The aim
is a smaller gap between the public window and the rest of the match, which cannot be measured
directly. External spellF1 will be reported, not predicted.

### Why This Is Not a Match-Specific Patch

It removes match-specific patches and forbids new ones by test. Only organiser-published facts stay,
and only in configuration.
