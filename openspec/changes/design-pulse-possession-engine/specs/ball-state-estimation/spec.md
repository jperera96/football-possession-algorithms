# Spec Delta

## Purpose

Make better use of ball observations during tracking gaps without inventing trajectories, by keeping
every estimate labelled, bounded and removable.

## ADDED Requirements

### Requirement: Ball state classification
Every frame SHALL have exactly one ball state: OBSERVED, INTERPOLATED, ESTIMATED or UNKNOWN. Original
observations MUST NOT be altered.

#### Scenario: Observation preserved
- **WHEN** reconstruction runs on a match
- **THEN** every OBSERVED frame keeps its original coordinates exactly

#### Scenario: Long occlusion
- **WHEN** a gap exceeds every configured limit
- **THEN** its frames are UNKNOWN and have no position

### Requirement: Conservative gap filling
A gap SHALL be filled only if its duration is within the configured limit and the implied motion
between the bounding observations is physically plausible.

#### Scenario: Short linear gap
- **WHEN** a short gap lies on a straight constant-speed synthetic pass
- **THEN** interpolated positions lie within the configured tolerance of the true path

#### Scenario: Implausible jump
- **WHEN** the implied speed across a gap exceeds the configured physical limit
- **THEN** the gap stays UNKNOWN

#### Scenario: Direction change in a gap
- **WHEN** a synthetic rebound occurs inside a gap
- **THEN** the estimate's uncertainty covers the true position or the gap stays UNKNOWN

#### Scenario: Recovery after absence
- **WHEN** an observation resumes after a gap
- **THEN** the state returns to OBSERVED on that frame with no smoothing of the observation

### Requirement: Uncertainty grows with absence
Each non-observed estimate SHALL carry a position uncertainty that does not decrease with the
distance in time from the nearest observation.

#### Scenario: Middle of a gap
- **WHEN** a gap is filled
- **THEN** uncertainty at its midpoint is at least that of frames nearer to its ends

### Requirement: Estimates cannot create hard facts
Estimated ball positions MUST NOT trigger out-of-bounds stoppages, touches or restart events on their
own. They MAY only contribute weak evidence.

#### Scenario: Interpolated ball outside the pitch
- **WHEN** an interpolated position falls outside the pitch and no observation does
- **THEN** no hard stoppage is produced

#### Scenario: Interpolated position near a player
- **WHEN** an interpolated position passes a player
- **THEN** no touch is registered

### Requirement: Evidence-gated adoption
Ball estimation SHALL be disabled in the default configuration until it passes the selection rule of
the external validation capability, and SHALL have a configuration switch for ablation.

#### Scenario: Module not validated
- **WHEN** the benchmark shows no qualifying benefit
- **THEN** the default configuration leaves estimation disabled and the decision is recorded
