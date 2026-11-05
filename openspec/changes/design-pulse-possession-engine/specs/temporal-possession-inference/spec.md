# Spec Delta

## Purpose

Convert frame evidence into coherent possession spells through interchangeable temporal decoders,
with explicit handling of uncertainty and of abstention as the official scorer treats it.

## ADDED Requirements

### Requirement: Common decoder interface
All temporal decoders SHALL consume the same evidence contracts and produce the same prediction contract.

#### Scenario: Swapping decoders
- **WHEN** configuration selects another decoder
- **THEN** the pipeline runs with no other code change

### Requirement: Decoding is independent per half
Decoders SHALL process each half separately. No spell MAY span a half boundary, and ungraded frames
SHALL be labelled X.

#### Scenario: Half boundary
- **WHEN** the same team holds the ball at the end of the first half and the start of the second
- **THEN** two separate spells are produced

### Requirement: Absent evidence is neutral
Frames with insufficient observation SHALL contribute no preference between H and A, so that
possession persists until evidence or a stoppage changes it.

#### Scenario: Long occlusion inside a possession
- **WHEN** a synthetic possession has a long ball absence with active players and the same team afterwards
- **THEN** one spell covers the interval

#### Scenario: Handover during an occlusion
- **WHEN** the team on each side of a gap differs
- **THEN** one transition is placed inside or at the edge of the gap, and its uncertainty is reported

### Requirement: Spell integrity
Decoders SHALL suppress transitions unsupported by sustained or decisive evidence, and MUST retain
short possessions supported by decisive evidence.

#### Scenario: Deflection
- **WHEN** an opponent touches the ball briefly and the original team regains it at once
- **THEN** the possession is not split

#### Scenario: Pass past a marker
- **WHEN** a pass flies near an opponent without a touch
- **THEN** no transition occurs

#### Scenario: Genuine short possession
- **WHEN** a synthetic team wins the ball, completes a pass and loses it within a few seconds
- **THEN** a separate spell is produced

#### Scenario: Fast counter-attack
- **WHEN** a recovery is followed immediately by a long pass in flight
- **THEN** the transition is placed at the recovery rather than at the reception

### Requirement: Boundary localisation
Spell boundaries SHALL be placed from the physical evidence of last and first control, and SHALL NOT
be delayed by the length of an evidence window.

#### Scenario: Clean handover
- **WHEN** a synthetic handover has a known frame
- **THEN** the decoded boundary falls within the configured tolerance

#### Scenario: Restart
- **WHEN** play restarts after a stoppage
- **THEN** the spell starts at the resolved restart frame within the configured tolerance

### Requirement: Stoppage integration
Decoders SHALL honour HARD stoppages, and SHALL treat D as a state that interrupts play without
forcing a change of team.

#### Scenario: Same team after a stoppage
- **WHEN** a HARD stoppage separates frames of one team
- **THEN** H or A resumes after D, and D frames remain labelled D

### Requirement: Offline use of context
Decoders MAY use past and future frames within a half. Results MUST be a deterministic function of
inputs and configuration.

#### Scenario: Repeated decoding
- **WHEN** a decoder runs twice on the same evidence
- **THEN** the outputs are identical, including tie-breaking

### Requirement: Evidence-based decoder selection
The default decoder SHALL change only if the challenger meets the selection rule of the external
validation capability. The refactored FSM SHALL remain the default otherwise.

#### Scenario: Inconclusive comparison
- **WHEN** a challenger's advantage is within the rule's margin
- **THEN** the simpler decoder stays the default

#### Scenario: Semi-Markov candidate
- **WHEN** no duration-specific failure of the first-order decoder has been measured
- **THEN** no hidden semi-Markov decoder is implemented

### Requirement: Abstention policy derived from the scorer
On graded frames the exporter SHALL write a definite label and MUST NOT write X, unless a test against
the official scorer shows a benefit. X SHALL be written on ungraded frames.

#### Scenario: Dominance check
- **WHEN** a synthetic prediction with X on graded frames is compared with the same prediction where each X is replaced by the scorer's fill value
- **THEN** spellF1 is equal and macroF1 of the explicit version is not lower

#### Scenario: Ungraded frames
- **WHEN** a frame is outside the configured graded intervals
- **THEN** its label is X

### Requirement: Uncertainty is reported outside the labels
The prediction SHALL include a per-spell and per-transition uncertainty record that names its cause:
insufficient evidence, signal conflict, low ball visibility, doubtful transition or ambiguous stoppage.

#### Scenario: Doubtful transition
- **WHEN** a transition has weak support
- **THEN** the record states the cause and the frames involved without changing the exported label

#### Scenario: Calibration claim
- **WHEN** uncertainty is described as calibrated
- **THEN** the claim cites a reliability measurement on authorised external data
