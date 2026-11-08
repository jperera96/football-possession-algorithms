# Analysis of `experiments/`

Source: `experiments/history.jsonl` (44 runs, 2026-10-28 to 2026-11-02), `experiments/EXPERIMENT_LOG.md`
and `experiments/README.md` at `54998ee`. Frame numbers in run notes are not repeated here.

## What the log records

Every run is scored against the public window only, frames 11,185 to 18,684 of the first half, with 17
ground-truth possessions. Fields: spellF1, macroF1, per-class F1, predicted possessions, mean duration,
fragmentation ratio, transition F1, mean latency, share error, abstentions, parameters, notes.

## Findings

| # | Finding | Evidence |
|---|---|---|
| E1 | The public window was the development feedback signal | `football_engine` versions go from 0.2769 to 0.9375 between runs 11 and 23 within two days, with notes describing a change per version |
| E2 | The score is saturated | Runs 23 to 43, 21 runs, are all at spellF1 0.9375. 0.9375 = 2 * 15 / (15 + 17): 15 matched possessions out of 15 predicted and 17 true, at every IoU threshold |
| E3 | Later work was evaluated elsewhere | Notes from run 21 onward refer to frames outside the public window and to "full-match" corrections, while the public score stays constant |
| E4 | Large uncertainty even out of sample | With 17 possessions, the Wilson 95% interval for recall 15/17 is about 0.66 to 0.97. The window is 4.7% of graded frames, all from the opening minutes |
| E5 | In-repo baselines differ from the official files | `baseline_smooth50` strategy scored 0.2900 (run 1); `experiments/README.md` gives 0.3256 for the official file. `smooth125`: 0.3733 versus 0.4242. Cause UNVERIFIED |
| E6 | The public-window trap is visible in the log itself | `smooth125` beats `smooth50` on the window (0.3733 versus 0.2900), the reverse of the official full-match result (0.2242 versus 0.2433) |
| E7 | Early alternatives were dropped on public scores alone | `hmm_viterbi` at 0.0083 and `fsm_advanced` at 0.2100 were set aside after one public run each |

## Consequences for this change

- 0.9375 is an in-sample, saturated, imprecise number. It is not an estimate of full-match quality.
- Keeping it as a target or floor would continue E1 and block changes that generalise.
- E3 means the corrections made outside the window were judged by watching the video. `RULES.md`
  allows watching to debug and to design features, and prohibits hand labels on the game for any
  purpose, and rules or constants tied to its frames. Which past changes fall on which side is for the
  team and the organisers to judge. This change makes future work measurable without that question.
- E5 is a reason to compare against the official baseline algorithm in the external suite, not only the in-repo strategy.

## How the log should be used from now on

Historical record only. Task 1.5 stops automatic public logging. New evidence goes to
`docs/engine/decisions.md`, with external results and the suite hash.
