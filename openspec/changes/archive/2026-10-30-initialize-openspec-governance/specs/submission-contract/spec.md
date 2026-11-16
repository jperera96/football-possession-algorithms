# Spec Delta

## Purpose

Records the submission file format that the unmodified official validator
(`evaluation/validate_submission.py`, `evaluation/possession_metrics.py:98-121`) accepts today.

## ADDED Requirements

### Requirement: Submission file format
A submission SHALL be a CSV with columns `frame` and `label`, exactly 199,319 rows whose `frame`
values are the integers 0..199318 in order, and every `label` SHALL be one of H, A, D or X after
trimming whitespace and upper-casing; the official validator MUST reject any other file with a
non-zero exit code.

#### Scenario: Valid file
- **WHEN** a file has header `frame,label`, rows 0..199318 in order and labels in H/A/D/X (any case)
- **THEN** the validator prints OK and exits 0

#### Scenario: Wrong row count
- **WHEN** the file has 199,318 rows
- **THEN** the validator fails with "row count"

#### Scenario: Non-contiguous frames
- **WHEN** a frame index is repeated or skipped
- **THEN** the validator fails because `frame` is not 0..199318 in order

#### Scenario: Unknown label
- **WHEN** a label is outside H, A, D, X
- **THEN** the validator fails listing the bad label

#### Scenario: Blank label
- **WHEN** a label cell is empty
- **THEN** the validator fails and asks for X instead of a blank

#### Scenario: Wrong header
- **WHEN** the header is not `frame,label`
- **THEN** the validator fails because it cannot read the expected columns
