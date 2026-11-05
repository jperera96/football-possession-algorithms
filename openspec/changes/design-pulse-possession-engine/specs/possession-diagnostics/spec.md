# Spec Delta

## Purpose

Help developers understand and compare pipeline decisions locally, without creating a route to
manual labelling or to publication of restricted information.

## ADDED Requirements

### Requirement: Decision traces
When tracing is enabled, a run SHALL emit a local trace giving, per segment, the label, duration, evidence summary, activated
rules, ball-state share and uncertainty cause.

#### Scenario: Explaining a transition
- **WHEN** a developer inspects a transition in a synthetic run
- **THEN** the trace shows the evidence and the rule or decoder step that produced it

#### Scenario: Tracing disabled
- **WHEN** tracing is off
- **THEN** the submission file is byte-identical to a traced run

### Requirement: Suspicion reports
Diagnostics SHALL list suspected fragmentation, transitions without sufficient evidence, long ball
absence, tag and tracking disagreement, kinematic jumps and weakly supported stoppages.

#### Scenario: Unsupported transition
- **WHEN** a synthetic transition has no supporting evidence
- **THEN** it appears in the report

### Requirement: A/B comparison without ground truth
The system SHALL compare two prediction files by segments, transitions and differing intervals, using
no ground truth of the provided game.

#### Scenario: Comparing two versions
- **WHEN** two runs differ
- **THEN** the comparison lists each differing interval and its evidence, with no score

### Requirement: Read-only tooling
Diagnostics MUST NOT provide any mechanism to enter, store or export human labels, corrections or
overrides, and pipeline stages MUST NOT read diagnostic output.

#### Scenario: Annotation attempt
- **WHEN** the tooling's interface is inspected by test
- **THEN** it has no input path that writes labels or corrections

#### Scenario: Feedback loop
- **WHEN** the pipeline runs
- **THEN** no diagnostics file is among its inputs

### Requirement: Diagnostics stay local
Diagnostics on the provided game SHALL be written only to ignored local paths, and MUST NOT export
frame-level tracking in a form that could reconstruct it. They SHALL run on synthetic data with no
match assets.

#### Scenario: Default output path
- **WHEN** a diagnostic runs on the provided game
- **THEN** its output path is ignored by Git

#### Scenario: Synthetic demonstration
- **WHEN** CI runs the diagnostics on a synthetic match
- **THEN** they complete without match assets
