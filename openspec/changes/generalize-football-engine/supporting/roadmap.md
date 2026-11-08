# Roadmap to 2026-11-17

Today is Sunday 2026-11-08 and the deadline is Tuesday 2026-11-17. Estimates are guesses: P0 is 7.5 pd,
P1 10 pd and P2 1.75 pd. Three people over the eight days from 9 to 16 November supply about 24 pd at
full time, so P0 and P1 fit with some margin, and P2 only if work runs ahead. Real availability is
decision D4.

## Gates

| Gate | Target | Meaning | If missed |
|---|---|---|---|
| G0 | Mon 9 Nov | PR 1 merged into `main`, this PR retargeted and merged; organiser questions sent | Each day lost comes out of task 2.9 |
| G1 | Wed 11 Nov | Tasks 1.1 to 1.10: compliant, game-independent, reproducible fallback | Everyone on P0; P1 limited to 2.2 to 2.6 |
| G2 | Sat 14 Nov | Task 2.10: algorithm frozen with recorded evidence | G1 fallback with rule decisions from 2.8 ships |
| G3 | Mon 16 Nov | Task 2.11: documents final, clean-clone rehearsal, repository public | Fix blockers only |
| Submit | Tue 17 Nov morning | A human submits the form | |

## Calendar

| Dates | Jordi | Raúl | Third member |
|---|---|---|---|
| 8 Nov | Review, decisions D1 to D5 | Review, 1.1 draft | Review, check Metrica terms |
| 9 Nov | 1.5 | 1.2, 1.4 | 1.3 |
| 10 Nov | 1.7 | 1.6 | 1.3, 2.2 |
| 11 Nov | 1.8, 1.10 (G1) | 1.9 | 2.2 |
| 12 Nov | 2.1 | 2.7 | 2.3, 2.4 |
| 13 Nov | 2.7 run (human-local), 2.8 | 2.5 support, 3.3 | 2.5, 2.6, 2.8 |
| 14 Nov | 2.9 | 3.2 if time | 2.9 support, 2.10 (G2) |
| 15 Nov | 2.9 tail, release candidate | 2.11 | 3.1 if time; write-up |
| 16 Nov | 2.11 (G3) | 2.11 | 2.11 |
| 17 Nov | Submit | Backup | Backup |

Joint points: G1, the 2.7 audit run, 2.8 decisions and G2. One person holds `strategies/football_engine.py` at a time.

## Cut list, in order

1. P2 (3.1 to 3.3).
2. 2.9 shrinks to the single most frequent external failure.
3. 2.7 drops perturbation stability and keeps the inside-versus-outside comparison.
4. 2.4 keeps ball dropout only.

Never cut: P0, the first external measurement (2.6), rule decisions (2.8), documents and the clean-clone rehearsal.

## Human-only actions

- Merge PR 1, then retarget this PR to `main` and merge it after review.
- Send organiser questions. `RULES.md` points to an issue, which would be public, so choose the channel.
- Run everything that needs match data; share only hashes, pass/fail and aggregate audit summaries.
- Audit the tree and history, make the repository public, and submit `<team_name>.csv` with the technical document.
