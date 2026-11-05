# Independent architecture review

Self-review by the author of this proposal, acting as a second architect. **It is not approval.**
Only human review and a merge into `main` approve this change.

| # | Question | Finding | Change made |
|---|---|---|---|
| 1 | Over-engineering? | Yes, in the first draft. A separate confidence module and abstention model were not justified | Merged confidence into temporal inference; P2 is optional |
| 2 | Duplicate modules? | Two state machines, two parsers, three stoppage sites exist today | Single owners; `runner` and `state_machine` retired |
| 3 | Does something already solve a need? | FSM, baseline, scorer bootstrap, validator, `games.py`, SRT tool | All reused |
| 4 | Technology without evidence? | Kalman, HSMM, kloppy in core | Rejected or deferred; kloppy limited to adapters |
| 5 | Clear route to a valid CSV? | Yes, G1 before any improvement | Fallback tagged |
| 6 | spellF1 prioritised? | Yes; boundary step added because delay costs spells | Boundary requirement |
| 7 | Can essentials ship in time? | P0 yes if approved by about 7 Nov; full P1 only at full time | Dependencies shortened; G2 moved to 14 Nov; cut list |
| 8 | Modules testable separately? | Yes, through contracts and a generator | Generator scheduled first |
| 9 | Too dependent on the match? | Residual: legacy thresholds and humans who have seen the match | Provenance register; stated as residual |
| 10 | Validation truly independent? | Partly. Event-derived labels are approximate, and design intuition is not independent | Two references; claim levels |
| 11 | Decoder complexity justified? | Not yet | Challenger only; HSMM gated |
| 12 | Can ball recovery add errors? | Yes | Off by default; no hard facts from estimates |
| 13 | Smart Tagging evidence or truth? | Today nearly truth for stoppages | Strength classes; conflict handling |
| 14 | Specs measurable? | Some tolerances are "configured" | Values must be set with provenance during implementation; scenarios remain testable on synthetic truth |
| 15 | Tasks decomposed enough? | Yes; 34 tasks, each with verification | |
| 16 | Will governance be respected? | Only by convention until branch protection exists | Documented; a human action |
| 17 | Favours reproducibility? | Yes | Entrypoint, cache, manifest, lockfile |
| 18 | What can be removed? | P2, Viterbi and ball estimation without harming a valid entry | Cut list |

## Errors corrected during review

- The first draft treated `games.py` offsets as the ATD conversion and called `frame_id - 1` a defect. `DATA.md` documents `frame_id - 1` as correct, and the offsets belong to another counter. Corrected in spec and design.
- P3 work as checkbox tasks would have prevented archiving. It is now listed as unapproved, with one closure task.
- `verification.md` is absent on purpose: the checker rejects it in a specification PR.

## Remaining weaknesses

- One umbrella change gives implementers wide `affected_areas`. Reviewers should check per-PR scope against the task's Files list, because the checker enforces only the union.
- `tasks.md` cannot be changed after approval without a specification PR, which is slow under a deadline. Tasks therefore allow a recorded rejection.
- Governance checks do not run on this stacked PR, since the workflow triggers only for `main`.
- Removing class-B rules may cost accuracy that cannot be measured legitimately.
