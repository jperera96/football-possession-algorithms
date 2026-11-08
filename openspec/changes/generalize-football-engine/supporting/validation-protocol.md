# Validation protocol

The external benchmark is a proxy for generalisation. It does not estimate the competition score.

## Datasets

| Dataset | Content | Terms | Use |
|---|---|---|---|
| [Metrica sample-data](https://github.com/metrica-sports/sample-data), games 1 to 3 | Tracking and events; games 1 and 2 in CSV, game 3 in EPTS and JSON; 25 fps observed in game 1 events; normalised coordinates | No licence file. The README asks for responsible use and acknowledgement. **Team to confirm** | Core suite. Same vendor and format family; events include PASS, RECOVERY, BALL LOST, BALL OUT, SET PIECE, CHALLENGE, SHOT |
| [IDSSE](https://doi.org/10.1038/s41597-025-04505-y) | Seven German matches, 25 fps positions, official events | CC BY 4.0 | Optional (task 3.1) |
| [SkillCorner opendata](https://github.com/SkillCorner/opendata) | Ten A-League matches, broadcast tracking | MIT repository licence | Not planned; possible robustness check later |

All concern other games, so their events are allowed (`RULES.md`). Data is downloaded by script into
an ignored path and listed in the technical document.

## Reference labels

- **v1 strict:** maximal runs of one team's on-ball events (PASS, RECOVERY, SHOT, completed carries), with flights attributed to the passer. From BALL OUT or a stoppage to the next SET PIECE or kickoff is D. Between BALL LOST and the next RECOVERY is ambiguous.
- **v2 relaxed:** as v1, with ambiguous gaps assigned to the team of the next controlled event.

Results are reported for both, with ambiguous intervals excluded and included.

## Corruption

Seeded, with strength levels including zero:

- Ball dropout up to about 41%, the published share for graded frames, more likely near duels, crowds and fast flights.
- Tracklet fragmentation up to 46 slots, swaps at crossings, occasional duplicates.
- Wrong team on some segments, including goalkeeper-like tracks.
- Coordinate noise.

Strengths come from public documentation, not from fitting to the competition tracking.

## Comparison

Engines: official baseline algorithm, the G1 fallback, and candidates from tasks 2.8 and 2.9. Metrics
come from `evaluation/possession_metrics.py`, used read-only: spellF1 first, macroF1 second, plus spell
count ratio and fragmentation. Results are per game, with paired bootstrap over spells within games.

## Selection rule (frozen in task 2.5)

A candidate becomes default only if all three hold on the frozen suite:

1. The lower bound of the paired 95% interval of its spellF1 difference is above 0.
2. Both reference variants agree in sign.
3. No corruption family is worse by more than 0.04.

Otherwise the simpler option stays. With three games, "inconclusive" will be common, and it is a valid
answer that keeps the simpler engine.

## What can be claimed

| Level | May be claimed |
|---|---|
| Synthetic and equivariance tests | "behaves as specified" |
| External suite | "better or worse against references v1 and v2 on these games" |
| Label-free audit | "behaves similarly, or differently, inside and outside the public window" |
| Competition match | "unknown" |
