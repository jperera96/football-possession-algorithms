# Spec Delta

## Purpose

Make the possession engine game-independent, so that it runs unchanged on any game in the internal
format and its behaviour can be measured, switched and justified rule by rule.

## ADDED Requirements

### Requirement: Game configuration holds only published facts
The engine SHALL read frame count, frame rate, pitch size and graded intervals from game
configuration. Configuration MUST NOT hold kicking teams, playing sides, track slots or any frame other
than organiser-published boundaries.

#### Scenario: Another game
- **WHEN** the engine runs on a game with other dimensions, frame count and graded intervals
- **THEN** it completes using that game's configuration with no code change

#### Scenario: Forbidden configuration key
- **WHEN** a configuration declares a kicking team, side or slot
- **THEN** loading fails naming the key

### Requirement: Match facts are inferred
Attack direction per half, kicking team per kickoff and team per tracklet segment SHALL be inferred
from tracking or automatic events, and each SHALL report unknown when evidence is insufficient.

#### Scenario: Teams swap ends at half-time
- **WHEN** a synthetic match swaps ends between halves
- **THEN** the inferred direction of each team reverses

#### Scenario: Goalkeeper tracklet with the wrong team
- **WHEN** a synthetic goalkeeper tracklet carries the opposing team's metadata and stays in its own defensive zone
- **THEN** its team is corrected, or it is flagged as low confidence, without using a slot number

#### Scenario: Kickoff team
- **WHEN** a synthetic kickoff is taken by one team
- **THEN** that team is inferred as the kicking team

#### Scenario: Insufficient evidence
- **WHEN** a half has too few valid frames to infer direction
- **THEN** direction is unknown and the rules that need it are disabled for that half

### Requirement: Equivariance
For the same inputs, mirroring the pitch SHALL leave labels unchanged. Exchanging team membership
SHALL exchange H and A, and leave D and X unchanged. Permuting track slots SHALL leave labels unchanged.

#### Scenario: Mirrored pitch
- **WHEN** x coordinates of a synthetic match are mirrored
- **THEN** the labels are identical

#### Scenario: Swapped teams
- **WHEN** team membership and tag team references are exchanged
- **THEN** H and A are exchanged in the output

#### Scenario: Permuted slots
- **WHEN** slot indices are permuted consistently
- **THEN** the labels are identical

### Requirement: Missing observations stay missing
Absent positions SHALL remain NaN. Ball speed and velocity MUST be undefined whenever a needed sample
is absent, and MUST NOT be replaced by zero or by sentinel distances.

#### Scenario: Ball reappears
- **WHEN** the ball is absent at frame t-1 and present at frame t
- **THEN** ball speed at frame t is undefined

#### Scenario: Stationary-ball rule on unknown speed
- **WHEN** a rule requires a stationary ball over frames with undefined speed
- **THEN** those frames do not count as stationary

### Requirement: Rules are identified and switchable
Every post-processing rule of the engine SHALL have a stable identifier and a configuration switch.
Turning a rule off SHALL remove only that rule's effect.

#### Scenario: All rules off
- **WHEN** every switchable rule is off
- **THEN** the engine returns the base state machine's output

#### Scenario: One rule off
- **WHEN** one rule is off on a synthetic match that triggers only that rule
- **THEN** the output differs exactly where the rule acted

### Requirement: Rule register
Each rule and parameter SHALL have a register entry with its rationale, origin, class and evidence
status. Class A depends on a match constant, class B has thresholds derived from observed cases, and
class C is physical or structural only.

#### Scenario: Unregistered rule
- **WHEN** a rule identifier has no register entry
- **THEN** the register test fails

#### Scenario: Class-B rule at algorithm freeze
- **WHEN** a class-B rule has no supporting external evidence at freeze
- **THEN** it is off by default, unless a maintainer decision consistent with any organiser answer is recorded

### Requirement: Evidence-driven engine changes
A change to engine behaviour SHALL be justified by external benchmark results, synthetic tests or
physical rationale, and SHALL arrive behind a switch. It MUST NOT be justified by frames of the
competition match.

#### Scenario: New rule
- **WHEN** a new rule is proposed
- **THEN** it has a switch, a register entry, a synthetic test and an external ablation result

#### Scenario: Fix motivated by a competition frame
- **WHEN** a change cites a frame of the competition match as its justification
- **THEN** it is rejected in review and logged in the compliance log

### Requirement: Engine stages are reachable by tests
The synthetic test suite SHALL reach every engine stage and every rule.

#### Scenario: Coverage of rules
- **WHEN** the synthetic suite runs
- **THEN** each rule identifier is reported as triggered at least once
