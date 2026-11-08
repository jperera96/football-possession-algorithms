# Spec Delta

## Purpose

Guarantee one official, deterministic and verifiable way of generating the submission file from a
clean clone and authorised inputs.

## ADDED Requirements

### Requirement: Single submission entrypoint
Exactly one documented command SHALL generate the submission, and no other tool MAY write a file
presented as the submission.

#### Scenario: Documented command
- **WHEN** a clean clone has the authorised inputs and the pinned environment
- **THEN** the documented command produces the submission file

#### Scenario: Retired path
- **WHEN** the former runner path is invoked
- **THEN** it no longer exists, or delegates to the single entrypoint

### Requirement: Deterministic output
Equivalent runs with the same inputs, configuration and environment SHALL produce byte-identical files.

#### Scenario: Two runs
- **WHEN** generation runs twice on a synthetic match
- **THEN** the SHA-256 of both files is equal

#### Scenario: Iteration order
- **WHEN** input records of equal content arrive in a different allowed order
- **THEN** the output is unchanged

### Requirement: Cache semantics
Caches SHALL be optional, regenerable, keyed by input hashes and code or schema version, and MUST NOT
change the output.

#### Scenario: With and without cache
- **WHEN** generation runs with no cache, then with a fresh cache
- **THEN** outputs are byte-identical

#### Scenario: Stale cache
- **WHEN** an input or schema version changes
- **THEN** the cache is rebuilt or ignored and the manifest says so

### Requirement: Versioned parameters
All parameters SHALL come from one version-controlled configuration, with units and provenance. The
run MUST fail on unknown or missing parameters.

#### Scenario: Unknown parameter
- **WHEN** the configuration contains an unknown key
- **THEN** the run stops before inference

### Requirement: Input validation and error handling
The entrypoint SHALL validate inputs before inference and exit non-zero on any failure, leaving no
file that looks complete.

#### Scenario: Failure during inference
- **WHEN** a stage raises an error
- **THEN** the process exits non-zero and the final path is not created or replaced

### Requirement: Run manifest
Each run SHALL write a manifest with commit, configuration hash, input hashes, environment versions,
output hash, decoder and whether tags and cache were used. It MUST NOT contain match data.

#### Scenario: Manifest content
- **WHEN** a run finishes
- **THEN** the manifest's output hash equals the file hash and it holds no labels or coordinates

#### Scenario: Dirty tree
- **WHEN** the working tree has uncommitted changes
- **THEN** the manifest marks the run as not releasable

### Requirement: Contract verification before success
A run SHALL report success only after the output passes the official submission validation. The
`submission-contract` capability remains the authority on format.

#### Scenario: Invalid output
- **WHEN** the official validator rejects the file
- **THEN** the run fails

### Requirement: Pinned environment
The project SHALL pin Python and all dependencies in a lockfile, and the documented installation SHALL
use it.

#### Scenario: Clean install
- **WHEN** the environment is created from the lockfile
- **THEN** resolved versions match the lockfile exactly

### Requirement: Effective quality gates
Test commands and CI SHALL exit non-zero on any failure. CI SHALL run contract, property, integration
and determinism tests on synthetic data, and skipped tests MUST NOT count as passing evidence.

#### Scenario: Failing strategy
- **WHEN** a strategy's synthetic test fails or raises
- **THEN** the test command exits non-zero

#### Scenario: Synthetic coverage
- **WHEN** CI runs the engine tests
- **THEN** every engine stage is reached on a synthetic match of sufficient length

### Requirement: Resource budget
Generation SHALL complete on a developer laptop, and each run SHALL record elapsed time and peak memory.

#### Scenario: Synthetic full-length run
- **WHEN** a synthetic match of the contract's frame count runs in CI
- **THEN** it stays within the configured time and memory budgets
