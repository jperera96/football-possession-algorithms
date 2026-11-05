# Spec Delta

## Purpose

Estimate, per frame, the evidence that each team controls the ball, using physical signals instead
of treating the nearest player as the possessor.

## ADDED Requirements

### Requirement: Four-channel frame evidence
For each frame the system SHALL produce separate evidence for H control, A control, no team in
control, and insufficient observation, together with the features that produced it.

#### Scenario: Clear control
- **WHEN** a synthetic player moves with the ball at close range and no opponent is near
- **THEN** that team's channel dominates

#### Scenario: Ball unobserved
- **WHEN** the ball state is UNKNOWN
- **THEN** only the insufficient-observation channel is active and neither team gains evidence

#### Scenario: No valid players
- **WHEN** no valid player of either team exists on a frame
- **THEN** the insufficient-observation channel is active

### Requirement: Control features beyond proximity
Team evidence SHALL use, where observable, minimum distance per team, the margin between teams,
relative player-ball velocity, persistence of contact and changes in ball direction.

#### Scenario: Nearest player without control
- **WHEN** a synthetic ball passes close to a player at high relative speed without changing direction
- **THEN** that player's team gains less evidence than a player moving with the ball at the same distance

#### Scenario: Touch signature
- **WHEN** ball direction or speed changes abruptly next to a player
- **THEN** a touch candidate with that team is recorded

### Requirement: Contested balls are distinguishable
The system SHALL represent contested situations separately from clear control of either team.

#### Scenario: Two teams at equal distance
- **WHEN** players of both teams are within the control range at similar distance
- **THEN** the frame is marked contested and neither team gains strong evidence

### Requirement: Scores are not probabilities unless calibrated
Evidence values MUST be labelled as scores unless calibration on authorised data has been measured,
and observation, evidence, calibrated probability and decision SHALL be distinct fields.

#### Scenario: Uncalibrated output
- **WHEN** a diagnostic displays an uncalibrated score
- **THEN** it is not labelled as a probability

#### Scenario: Calibrated output
- **WHEN** a model is reported as calibrated
- **THEN** its calibration report names the dataset and shows the measured error
