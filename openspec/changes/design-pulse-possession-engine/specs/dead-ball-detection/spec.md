# Spec Delta

## Purpose

Provide a single source of truth for stoppages and restarts that separates real interruptions from
simple loss of ball tracking.

## ADDED Requirements

### Requirement: Single owner of stoppage decisions
All dead-ball evidence SHALL be produced by one component. Other modules MUST NOT create or remove
dead-ball intervals except through its documented output.

#### Scenario: Duplicate logic
- **WHEN** a stoppage rule is required by a decoder
- **THEN** the decoder consumes dead-ball evidence and has no stoppage rule of its own

### Requirement: Graded evidence strength
Dead-ball evidence SHALL distinguish HARD stoppages, SOFT stoppage evidence and NONE. Decoders MUST
respect HARD and MAY weigh SOFT against other evidence.

#### Scenario: Observed ball clearly out of bounds
- **WHEN** an observed ball is beyond the pitch by more than the configured margin for the configured time
- **THEN** a HARD stoppage is produced

#### Scenario: Touchline graze
- **WHEN** an observed ball leaves the pitch briefly and shallowly with in-play motion on both sides
- **THEN** no HARD stoppage is produced

### Requirement: Ball absence is not a stoppage
Ball absence alone MUST NOT produce dead-ball evidence above SOFT, and SHALL be combined with
collective player behaviour or automatic events.

#### Scenario: Occlusion with active players
- **WHEN** the ball is absent and collective player speed stays at match intensity
- **THEN** no stoppage is produced

#### Scenario: Absence with collective deceleration
- **WHEN** the ball is absent and collective player speed falls below the walking threshold for the configured time
- **THEN** SOFT stoppage evidence is produced

### Requirement: Stoppage types without fixed sides
The detector SHALL handle throw-ins, corners, goal kicks, free kicks, offsides, goals and kickoffs
using general geometry and inferred match facts, and MUST NOT assume a side or a team.

#### Scenario: Untagged in-pitch free kick
- **WHEN** a synthetic ball is stationary with collective deceleration and is then struck
- **THEN** a stoppage ending at the strike is detected with no tag present

#### Scenario: Live slow build-up
- **WHEN** a defender holds a slow-moving ball under no pressure while players keep moving
- **THEN** no stoppage is produced

#### Scenario: Goal then kickoff
- **WHEN** a synthetic goal is followed by a celebration and a kickoff at the centre
- **THEN** a stoppage spans the interval and ends at the kickoff

### Requirement: Restart resolution
The detector SHALL estimate the restart frame and team from ball motion, player positions and
automatic events, and SHALL report unknown when evidence is insufficient.

#### Scenario: Throw-in without team tag
- **WHEN** a tagged throw-in has no team and a player stands at the touchline next to the restart
- **THEN** that player's team is proposed with its source recorded

#### Scenario: Unknown restart team
- **WHEN** no restart team can be determined
- **THEN** the decoder receives unknown and resolves the team from team evidence

#### Scenario: Tag earlier than execution
- **WHEN** a restart tag precedes the observed strike
- **THEN** the stoppage ends at the observed strike, within the configured search limit

### Requirement: Short unverified stoppages do not split possessions
SOFT evidence that would create a short stoppage between frames of the same team, with no HARD
support, MUST NOT split the possession.

#### Scenario: Brief false stoppage
- **WHEN** a short SOFT interval has the same team on both sides
- **THEN** the possession remains one spell in the output
