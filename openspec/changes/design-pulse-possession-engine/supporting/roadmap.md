# Roadmap to 2026-11-17

Today is Thursday 2026-11-05, and the deadline is Tuesday 2026-11-17. Estimates are guesses, not
measurements. P0 is 11.25 pd and P1 is 16.5 pd, which is 27.75 pd in total. Three people working full
days on all nine days from 7 to 15 November supply 27 pd. **So P1 fits only with full-time availability
and no slippage. Availability is unknown (decision D4), and the cut list is part of the plan.**

## Gates

| Gate | Target | Meaning | If missed |
|---|---|---|---|
| G0 | Fri 6 Nov | PR 1 and this specification merged; organiser questions sent | Reduced P0 specification PR; P1 scope shrinks one for one |
| G1 | Wed 11 Nov | Tasks 1.1 to 1.14 done: compliant, reproducible fallback | All effort stays on P0; P1 cut to validation only |
| G2 | Sat 14 Nov | Task 2.11 done: algorithm freeze, decoder and class-B decisions | Refactored engine ships, new modules disabled |
| G3 | Mon 16 Nov | Task 2.14 done: clean-clone rehearsal, document final, repository public | No new work; fix blockers only |
| Submit | Tue 17 Nov morning | A human submits the form | |

## Calendar

| Dates | Jordi: core engine | Raúl: architecture and engineering | Third member: research and validation |
|---|---|---|---|
| 5 to 6 Nov | Review; decisions D1 to D5; merge PR 1 | Review support; 1.1 | Review; read dataset terms |
| 7 Nov | 1.12 | 1.7, 1.4 | 1.2 |
| 8 Nov | 1.9 | 1.8 | 1.2 |
| 9 Nov | 1.9 | 1.5, 1.3 | 2.1, 2.2 |
| 10 Nov | 1.6, 1.10 | 1.11 | 2.2 |
| 11 Nov | 1.10, 1.13, 1.14 (G1) | 1.13, integration | 2.3 |
| 12 Nov | 2.6 | 2.7 | 2.3, 2.4 |
| 13 Nov | 2.6, 2.8 | 2.7, 2.8 | 2.4, 2.5 |
| 14 Nov | 2.8, 2.9 | 2.13, then 2.10 or 2.12 if time allows | 2.5, 2.9, 2.11 (G2) |
| 15 Nov | Release candidate | Release; P2 only if ahead | Benchmark write-up |
| 16 Nov | 2.14 together (G3) | 2.14 | 2.14 |
| 17 Nov | Submit | Backup | Backup |

**Schedule risk.** This calendar leaves no slack, and the benchmark is ready only around 14 November.
So 2.10 (Viterbi) and 2.12 (ball estimation) are unlikely to finish unless someone runs ahead, and
2.11 would then just confirm the FSM. That outcome is acceptable.

P0 critical path by dependency: 1.7, 1.9, 1.10, 1.13, 1.14, about 4.75 pd serial. The owner split
follows the proposal in the brief and assumes nothing about the third member's speciality. GitHub
lists a third collaborator, `crafegas96`; roles are for the team to confirm.

## Parallel work and joint points

Parallel from the start: validation (2.1 to 2.5) depends only on 1.4 and 1.7. Contracts, tests and
environment are independent of the engine. Joint points: 1.10 and 1.11 at G1; 2.8 needs 2.6 and 2.7;
G2 decision; release. One owner holds `strategies/football_engine.py` at a time.

## Cut list, in order

1. All of P2.
2. 2.12 ball estimation.
3. 2.10 and 2.11 Viterbi. The FSM ships.
4. 2.2 IDSSE adapter part.
5. 2.8 stage moves, if unfinished by 13 Nov. Ablation can use simple flags on the engine instead.
6. 2.6, 2.7, if G1 slipped.

Never cut: P0, class-B decisions (at least by maintainer judgement), the technical document, the
repository audit and clean-clone regeneration.

## Human-only actions

- Merge PR 1, then retarget this PR to `main` (it is stacked on `raulrn/openspec-init`).
- Send organiser questions. `RULES.md` directs questions to an issue, which would be public, so choose the channel deliberately.
- Run anything using match data; report only hashes and pass/fail.
- Make the repository public before submission. This is also what makes branch protection available on the current plan. Audit tree and history first.
- Submit the form with `<team_name>.csv` and the technical document named after the team.

## P3, after the deadline

Not authorised under this change: video ball detection with Supervision, video-based recovery,
broadcast and tactical synchronisation, HSMM, Kalman smoothing, 3D ball, models on larger datasets,
product dashboard, production infrastructure.
