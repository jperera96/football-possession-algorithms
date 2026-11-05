# Spec Delta

## Purpose

Use Metrica's automatic Smart Tagging as weighted, optional evidence, so that tags inform inference
without being imposed as ground truth.

## ADDED Requirements

### Requirement: Tags are evidence, not truth
Smart Tagging SHALL be converted into evidence with a declared strength and source. It MUST NOT
overwrite labels directly, apart from HARD stoppages confirmed by the dead-ball detector.

#### Scenario: Tag without physical support
- **WHEN** a stoppage tag covers an interval with clear live play
- **THEN** the tag's evidence is reduced and the conflict is recorded

### Requirement: Evidence strength classes
Each tag type SHALL map, through versioned configuration, to one class: strong, weak, contextual or ignored.

#### Scenario: Restart tag
- **WHEN** a set-piece tag is parsed
- **THEN** it yields restart evidence with its configured class

#### Scenario: Unknown tag type
- **WHEN** an unmapped tag type appears
- **THEN** it is ignored and counted in the ingestion report

### Requirement: Phase team tags are interval context
A team tag on a tactical phase MUST NOT be interpreted as possession on every frame of its interval.
It MAY contribute only weak evidence.

#### Scenario: Phase contradicts tracking
- **WHEN** a phase tag names one team while team evidence clearly favours the other for a sustained period
- **THEN** the decoded possession follows the tracking evidence

### Requirement: Missing, ambiguous and contradictory tags
Missing, ambiguous or contradictory tags SHALL reduce evidence, never raise an error during inference.

#### Scenario: Tag team not available
- **WHEN** a tag has no team
- **THEN** the team field is unknown and no team evidence is emitted

#### Scenario: Contradictory overlapping tags
- **WHEN** overlapping tags imply different teams
- **THEN** both are retained in diagnostics and their team evidence cancels

### Requirement: Inference works without tags
The full pipeline SHALL run with no tagging input, and results SHALL report whether tags were used.

#### Scenario: External game
- **WHEN** a public game has no Smart Tagging
- **THEN** the pipeline completes and the run manifest states that tags were absent

### Requirement: Team references come from metadata
Tag team names SHALL be mapped to H and A from the game's metadata, and MUST NOT use names in code.

#### Scenario: Another game's teams
- **WHEN** a synthetic game uses other team names
- **THEN** tags map to H and A correctly

### Requirement: Fusion benefit is not assumed
Fusion weights beyond existing restart and stoppage use SHALL stay disabled unless measured on
simulated tag noise, and reports MUST state that public games lack equivalent Smart Tagging.

#### Scenario: Reporting a fusion result
- **WHEN** a fusion benefit is reported
- **THEN** the report says it comes from simulated tags, and makes no claim about the competition match
