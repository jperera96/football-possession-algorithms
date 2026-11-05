# External validation protocol

Purpose: a legitimate selection signal. It is a proxy. It does not estimate the competition score.

## Datasets (register candidates)

| Dataset | Content | Terms | Fit | Limits |
|---|---|---|---|---|
| [Metrica sample-data](https://github.com/metrica-sports/sample-data) games 1 to 3 | Tracking and events; games 1 and 2 in CSV, game 3 in EPTS and JSON; 25 fps on inspection of game 1 events; normalised coordinates | No licence file. README asks for responsible use and acknowledgement. **Team must confirm suitability** | First choice: same vendor and format family; events include PASS, RECOVERY, BALL LOST, BALL OUT, SET PIECE, CHALLENGE, SHOT | Three games; anonymised; no Smart Tagging; ball quality may differ (UNVERIFIED); last updated 2021 |
| [IDSSE](https://doi.org/10.1038/s41597-025-04505-y) | Seven German matches, positions at 25 fps, official events | CC BY 4.0 ([data](https://doi.org/10.6084/m9.figshare.28196177)) | Independent provider; more games; kloppy-compatible through a [mirror](https://huggingface.co/datasets/pysport/idsse-data) | Different event definitions; adapter cost; stretch goal |
| [SkillCorner opendata](https://github.com/SkillCorner/opendata) | Ten A-League matches, broadcast tracking, dynamic events | MIT repository licence | Real occlusion patterns, so optional robustness only | Different geometry and quality; events are not a possession reference |

All concern other games, so event data and hand labels on them are allowed by `RULES.md`. Everything
used must stay accessible and be listed in the technical document. Data is fetched to an ignored
path, and not committed.

## Reference labels

Event streams do not equal the organisers' ground truth. Definitions:

- **v1 strict:** a spell is a maximal run of on-ball events of one team (PASS, RECOVERY, carries implied between them, SHOT) with flights attributed to the passer. BALL OUT, stoppage or goal to next SET PIECE or kickoff is D. Periods between BALL LOST and RECOVERY are ambiguous.
- **v2 relaxed:** same, with ambiguous gaps assigned to the team of the next controlled event.

Ambiguous masks are excluded in one analysis and included in the other. Both are versioned, and any
conclusion must hold on both variants or is reported as sensitive to the definition.

## Corruptions

Seeded, each with strength levels including zero:

| Family | Basis |
|---|---|
| Ball dropout to about the published 41%, more likely near crowds, duels and flights | `DATA.md`, `FAQ.md` |
| Tracklet fragmentation into up to 46 slots, swaps at crossings, duplicates | `DATA.md` |
| Wrong team on some segments, including goalkeeper-like tracks | Generic failure of automatic tracking |
| Coordinate noise, aerial projection displacement | Generic |
| Synthetic tags from events with false positives, false negatives and jitter | `FAQ.md`: tags have errors both ways |

Parameters come from public documentation. Fitting them to private tracking is not planned, and
would need a separate decision.

## Measures

Official functions only, imported read-only from `evaluation/possession_metrics.py`: spellF1 first,
macroF1 second. Diagnostic: spell count ratio, fragmentation, transition timing, boundary error,
short-spell recall, false D rate. Comparators: baseline windows, current engine with constants
replaced, refactored FSM, Viterbi.

## Statistics

Leave-one-game-out for anything fitted (emission bins, transition costs). Paired bootstrap over
spells within games, and per-game differences shown individually. Few games mean wide intervals, and
"inconclusive" is a legitimate result.

## Pre-declared selection rule

Frozen with a hash before candidate results exist (task 2.5). A more complex option replaces a simpler
one only if all hold on the external suite:

1. The lower bound of the 95% paired interval of the spellF1 difference is above 0.
2. The spellF1 difference is at least 0.04, the noise band `EVALUATION.md` gives for the full match.
3. No corruption family is worse by more than 0.04.
4. Both reference variants agree in sign.

Rule 2 borrows the official band as a practical margin, because the band for this suite is unknown.

## Levels of claim

| Level | Source | May be claimed |
|---|---|---|
| 1 Implementation correctness | unit, property tests | "meets its contract" |
| 2 Synthetic robustness | generator, corruption | "robust to X in simulation" |
| 3 External reference | public games | "better against reference v1, v2" |
| 4 Generalisation | leave-one-game-out | "consistent across N games" |
| 5 Private performance | none | "unknown" |

## Exclusions

The benchmark refuses the competition game and its public ground truth. Hand labels on the provided
game do not exist in this design. Hand labels on other games are allowed, and not planned.
