# Spec Delta

## Purpose

Define what the possession system and its repository must never contain or claim, and how those
competition rules are checked automatically or escalated to a human decision.

## ADDED Requirements

### Requirement: No match-specific constants in inference
Inference code SHALL NOT contain frame numbers, spell boundaries, team names, playing sides or track
slot numbers of the provided game. Organiser-published per-game facts SHALL exist only in game
configuration.

#### Scenario: Frame literal in inference code
- **WHEN** a module under `strategies/` or `pipeline/` contains a literal equal to a graded boundary or kickoff frame of the configured game
- **THEN** the static compliance test fails and names the file and line

#### Scenario: Team name in a parser
- **WHEN** inference code compares text against a specific club name
- **THEN** the static compliance test fails

#### Scenario: Published fact in configuration
- **WHEN** a frame count or graded interval is read from game configuration
- **THEN** the static compliance test passes

### Requirement: No hand labels on the provided game
The repository MUST NOT contain tests, fixtures, labels, corrections or expected outputs that encode
human judgements about possession at specific frames of the provided game, whatever their purpose.

#### Scenario: Frame-window assertion on the provided game
- **WHEN** a test asserts an expected label over a frame window of the provided game
- **THEN** the static compliance test fails

#### Scenario: Synthetic or external expectation
- **WHEN** a test asserts an expected label on a synthetic match or an authorised other game
- **THEN** the static compliance test passes

### Requirement: Public ground truth limited to pipeline checks
The public 5-minute ground truth MUST NOT feed training, tuning, parameter sweeps, algorithm or
window selection, metric floors or regression gates. It MAY be used to check alignment and format.

#### Scenario: Gate on a public metric
- **WHEN** a quality gate compares a public-window score with a threshold
- **THEN** the static compliance test fails

#### Scenario: Automated sweep
- **WHEN** a tool iterates over parameter values or engine versions and scores them against the public ground truth
- **THEN** the static compliance test fails

#### Scenario: Pipeline sanity check
- **WHEN** a human runs the official evaluation to confirm that a file is aligned and well-formed
- **THEN** no selection, threshold or log entry is derived from the result

#### Scenario: Public score falls after a generalisation change
- **WHEN** a change accepted on external evidence lowers the public-window score
- **THEN** the change is not reverted for that reason alone

### Requirement: Full-match labels stay out of Git
The repository MUST NOT track full-match predicted labels of the provided game, in any encoding,
apart from the organiser-supplied baseline files.

#### Scenario: Committed label snapshot
- **WHEN** a tracked file outside `evaluation/results/baseline_*.csv` holds run-length or per-frame labels for the provided game
- **THEN** the compliance check fails

#### Scenario: Local comparison
- **WHEN** a developer compares two local runs
- **THEN** the compared artifacts live in an ignored local directory

### Requirement: Compliance questions are escalated and logged
Doubts about past or planned practice SHALL be recorded in a compliance log and raised with
organisers by a human. Historical evidence MUST NOT be erased or rewritten.

#### Scenario: Open question at release
- **WHEN** a release candidate is prepared while a blocking compliance question has no recorded answer or maintainer decision
- **THEN** the release checklist fails

#### Scenario: Removing a non-compliant artifact
- **WHEN** a non-compliant file is removed from the current tree
- **THEN** the compliance log records what was removed, why and the commit, and Git history is left intact

### Requirement: Technical document matches the repository
The technical document SHALL describe the data, labels and evaluation practice actually used,
including relevant project history, and MUST NOT present public-window scores as full-match estimates.

#### Scenario: Unsupported claim
- **WHEN** the release checklist compares the document's compliance statements with the compliance log
- **THEN** every statement is supported by the log or is corrected before submission

#### Scenario: Public-window score
- **WHEN** the document mentions a public-window score
- **THEN** it is labelled as a pipeline check, or it is removed
