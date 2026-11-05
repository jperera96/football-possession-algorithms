# Spec Delta

## Purpose

Define the stable data contracts between possession modules: indexing, units, missing values,
tracklet semantics, inferred match facts, data layers and validation.

## ADDED Requirements

### Requirement: Single ingestion path
The system SHALL load tracking, metadata and tagging through one ingestion implementation used by
every entrypoint, strategy and tool.

#### Scenario: Two consumers
- **WHEN** the submission entrypoint and the diagnostics tool load the same inputs
- **THEN** they receive identical arrays

#### Scenario: Missing asset
- **WHEN** a required input is absent
- **THEN** ingestion stops with an error naming the file and produces no partial context

### Requirement: Frame and time indexing
The video frame index SHALL be the only frame index exposed to modules. Each source SHALL declare its
conversion to video frames, and time SHALL be derived from the configured frame rate.

#### Scenario: One-based tracking identifiers
- **WHEN** a synthetic source declares identifiers starting at 1
- **THEN** the first record lands on video frame 0 and the last on the final frame

#### Scenario: Record outside the video
- **WHEN** a tracking record maps outside the video frame range
- **THEN** it is excluded and counted in the ingestion report

### Requirement: Coordinate and unit conventions
Modules SHALL receive positions in metres, in a pitch frame derived from configured pitch dimensions,
and speeds in metres per second. Normalised coordinates SHALL remain available as raw observations.

#### Scenario: Different pitch size
- **WHEN** a game is configured with other pitch dimensions
- **THEN** distances and pitch regions scale without code changes

### Requirement: Missing observations are explicit
Absent positions SHALL remain NaN with an explicit validity mask. Velocity, speed and acceleration
MUST be undefined whenever a required sample is absent, and MUST NOT be replaced by zero.

#### Scenario: Ball absent then present
- **WHEN** the ball is absent at frame t-1 and present at frame t
- **THEN** ball speed at frame t is undefined rather than zero

#### Scenario: Stationary test on an unknown speed
- **WHEN** a rule requires a stationary ball over frames whose speed is undefined
- **THEN** those frames do not count as stationary

### Requirement: Tracklets are not identities
Modules MUST NOT assume that a track slot identifies one player over time, and MUST NOT give meaning
to a slot number.

#### Scenario: Slot permutation
- **WHEN** track slot indices are consistently permuted in a synthetic match
- **THEN** the output labels are unchanged

#### Scenario: Tracklet interruption
- **WHEN** a player's track moves to a new slot mid-match
- **THEN** team evidence continues from the positions without any per-slot history being required

### Requirement: Inferred team assignment for tracklets
The system SHALL estimate team membership per tracklet segment from metadata and observed behaviour,
and SHALL expose the assignment together with a confidence value. Goalkeeper handling MUST NOT rely on fixed slots.

#### Scenario: Goalkeeper track under the wrong team
- **WHEN** a synthetic goalkeeper tracklet carries the opposing team's metadata while staying in its own defensive zone
- **THEN** the segment is reassigned, or flagged as low confidence, without using a slot number

#### Scenario: Ambiguous segment
- **WHEN** a short tracklet has no reliable team signal
- **THEN** it keeps its metadata team and is marked low confidence

### Requirement: Inferred match facts
Attacking direction per half and the kicking team at each kickoff SHALL be inferred from tracking or
automatic evidence, and MUST NOT be configured per match.

#### Scenario: Direction inference
- **WHEN** a synthetic match swaps ends at half-time
- **THEN** the inferred direction of each team reverses between halves

#### Scenario: Insufficient evidence
- **WHEN** a half has too few valid frames to infer direction
- **THEN** direction is reported as unknown and direction-dependent rules are disabled for that half

### Requirement: Mirror and team-swap equivariance
For the same inputs under a pitch mirror, labels SHALL be unchanged. Under an exchange of team
membership, H and A SHALL be exchanged and D and X SHALL be unchanged.

#### Scenario: Mirrored pitch
- **WHEN** x coordinates of a synthetic match are mirrored
- **THEN** output labels are identical

#### Scenario: Swapped teams
- **WHEN** team membership and tag team references are exchanged
- **THEN** H and A are exchanged in the output

### Requirement: Separated data layers with provenance
Raw observations, reconstructed values, evidence, decoded states and exportable results SHALL be
separate structures. Derived values SHALL carry their source, and stages MUST NOT mutate their inputs.

#### Scenario: Stage input immutability
- **WHEN** a stage runs on a read-only input
- **THEN** it completes without modifying the input

#### Scenario: Provenance query
- **WHEN** a frame's ball position is reconstructed
- **THEN** its layer records the reconstruction method and keeps the original absence visible

### Requirement: Contract validation
Each contract SHALL validate shapes, dtypes, ranges and invariants at construction, and SHALL fail
with a message that names the violated invariant.

#### Scenario: Shape mismatch
- **WHEN** a mask length differs from the number of frames
- **THEN** construction fails naming the field

#### Scenario: Empty match
- **WHEN** a context has zero frames
- **THEN** the pipeline returns an empty result or a contract error, and never writes out of range
