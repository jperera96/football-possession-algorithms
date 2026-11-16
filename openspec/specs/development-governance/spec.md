# development-governance Specification

## Purpose
Guarantees that every repository change is specified, approved by a human through the protected
branch, implemented within its approved scope and backed by verification evidence.

## Requirements

### Requirement: Specification before implementation
The governance check SHALL reject any pull request that changes files outside a single change's
planning directory unless it declares an OpenSpec change that already exists, unarchived, in the
trusted base revision of the protected branch.

#### Scenario: Code change without a declared change
- **WHEN** a pull request modifies `strategies/engine.py` and declares no `OpenSpec-Change`
- **THEN** the check fails with a non-zero exit code and explains that an approved change is required

#### Scenario: Dependency, CI or agent-instruction change without a declared change
- **WHEN** a pull request modifies `requirements.txt`, a workflow under `.github/` or `AGENTS.md` without a declared change
- **THEN** the check fails

#### Scenario: Change introduced in the same pull request
- **WHEN** a pull request adds `openspec/changes/<id>/` and implementation files and declares `<id>`
- **THEN** the check fails because `<id>` is not present in the base revision

#### Scenario: Nonexistent or archived change
- **WHEN** the declared change does not exist in the base revision, or exists only under `openspec/changes/archive/`
- **THEN** the check fails

### Requirement: Approval provenance
The governance check MUST NOT accept approval from any content of the pull request; a change
SHALL count as approved only when its planning artifacts exist in the base revision of the
protected branch, and the check SHALL reject a base that belongs to another branch or is not
contained in a trusted reference when one is given.

#### Scenario: Fake approval markers
- **WHEN** a pull request adds `approved: true` to `.openspec.yaml`, "Approved-by" lines to the proposal and "/approve" to its description
- **THEN** the markers are ignored and the check fails if the change is not in the base

#### Scenario: Untrusted base branch
- **WHEN** the pull request targets a branch other than `main`, or the base commit is not contained in the trusted reference
- **THEN** the check fails

### Requirement: Pull request classification
The governance check SHALL classify each pull request as bootstrap, specification,
implementation or governance and MUST fail when the change set is empty, mixes planning of
another change into an implementation, uses unsafe paths, symlinks, submodules or type changes,
or when the base revision cannot be resolved.

#### Scenario: Valid specification pull request
- **WHEN** a pull request only adds complete planning artifacts for one change
- **THEN** it is classified as specification and passes

#### Scenario: Implementation smuggling a second specification
- **WHEN** an implementation pull request for an approved change also adds the planning of another change
- **THEN** the check fails

#### Scenario: Unresolvable base
- **WHEN** the base revision does not exist or looks like a command-line option
- **THEN** the check exits with status 2 without classifying

#### Scenario: Unexpected path characters
- **WHEN** a changed path contains a newline or characters outside `[A-Za-z0-9._@+-/ ]`
- **THEN** the check fails and names the path

### Requirement: Planning artifact completeness
A change's planning SHALL use the `pulse-governed` schema and contain a proposal, a design and
tasks with every required section filled, and SHALL contain valid delta specs unless it declares
`skip_specs: true`; algorithm changes SHALL also answer the Algorithm Review and Possession
Engine Considerations.

#### Scenario: Empty or placeholder proposal
- **WHEN** a proposal section is missing, empty or only a placeholder such as "TBD" or a template comment
- **THEN** the check fails naming the section

#### Scenario: Missing design or tasks
- **WHEN** `design.md` or `tasks.md` is absent
- **THEN** the check fails

#### Scenario: Invalid delta spec
- **WHEN** a requirement lacks a SHALL or MUST statement or a `#### Scenario:` with **WHEN** and **THEN**
- **THEN** the check fails

#### Scenario: Untraceable tasks
- **WHEN** a task lacks Depends on, Files, Requirements, Verification or Done when, or references no requirement of the change
- **THEN** the check fails

### Requirement: Approved scope
An implementation pull request SHALL only modify files matched by the approved change's
`affected_areas`, MUST NOT modify the approved proposal, design or specs or the text of its
tasks, and MUST NOT modify protected governance or official competition paths unless an
`affected_areas` pattern rooted in that protected path was approved.

#### Scenario: Unapproved scope expansion
- **WHEN** an implementation modifies a file outside `affected_areas`, including through a rename
- **THEN** the check fails and asks for a specification amendment

#### Scenario: Protected path through a broad glob
- **WHEN** `affected_areas` contains `tests/**` and the pull request edits `tests/governance/test_check_openspec.py`
- **THEN** the check fails because protected paths need a pattern rooted in them

#### Scenario: Algorithm code under a non-algorithm proposal
- **WHEN** an approved `Type: non-algorithm` change modifies `strategies/`, `pipeline/`, `run_experiment.py` or `games.py`
- **THEN** the check fails

### Requirement: Verification evidence
An implementation pull request SHALL include `verification.md` with every required section,
SHALL mention every requirement of the change under Requirement Coverage, SHALL report
`Status: COMPLETE` exactly when all tasks are checked, and SHALL change Python code only together
with a test.

#### Scenario: Tasks checked without evidence
- **WHEN** tasks are checked and `verification.md` is missing
- **THEN** the check fails

#### Scenario: Specification pull request marks tasks done
- **WHEN** a specification pull request checks tasks or adds `verification.md`
- **THEN** the check fails

### Requirement: Archive integrity
Archiving a change SHALL move it unchanged (apart from task checkboxes and verification evidence)
to `openspec/changes/archive/YYYY-MM-DD-<id>/` with all tasks checked and `Status: COMPLETE`, and
main specs under `openspec/specs/` SHALL change only through such an archive of a change that owns
the capability.

#### Scenario: Valid archive in the implementation pull request
- **WHEN** the implementation pull request moves the approved change to the archive with all tasks checked and syncs its capability spec
- **THEN** the check passes

#### Scenario: Altered or incomplete archive
- **WHEN** the archived proposal differs from the approved one or tasks remain unchecked
- **THEN** the check fails

### Requirement: One-time bootstrap
The governance check SHALL accept a bootstrap only while the base revision has neither the
governance checker nor `openspec/config.yaml`, only for governance files and `DEVELOPING.md`,
only with the documented change `initialize-openspec-governance`, and MUST NOT accept deletions
or algorithm changes in a bootstrap.

#### Scenario: Bootstrap touching algorithms
- **WHEN** a bootstrap pull request also modifies `strategies/engine.py`
- **THEN** the check fails

#### Scenario: Bootstrap after governance exists
- **WHEN** governance exists in the base and a pull request deletes it while changing code
- **THEN** the check does not use bootstrap mode and fails

### Requirement: Confidential data independence
The governance check SHALL decide using only Git metadata and repository text files and MUST NOT
execute the possession engine or read private competition assets.

#### Scenario: Running the check in CI
- **WHEN** the check runs in GitHub Actions without the competition data
- **THEN** it completes its classification and validation
