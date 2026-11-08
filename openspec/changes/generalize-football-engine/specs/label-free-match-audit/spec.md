# Spec Delta

## Purpose

Inspect the engine's behaviour over the whole competition match without any labels, to detect
behaviour that is specific to the public window or to individual moments.

## ADDED Requirements

### Requirement: Aggregate-only output
The audit SHALL print only aggregate statistics. It MUST NOT print or write per-frame labels, frame
numbers of events, coordinates or tracking excerpts, and MUST NOT read the public ground truth.

#### Scenario: Report content
- **WHEN** the audit runs on the competition match
- **THEN** its output contains counts, rates and distribution summaries only

#### Scenario: Ground truth present
- **WHEN** the public ground truth file exists
- **THEN** the audit does not open it

### Requirement: Inside versus outside the public window
The audit SHALL compare, between the published public window and the rest of the graded match:
activation rate per rule, possession rate, spell duration distribution, D share and short-spell share.

#### Scenario: Rule concentrated in the window
- **WHEN** a rule's activation rate inside the window exceeds three times its rate outside, or the reverse, with enough activations to compare
- **THEN** the rule is flagged for review in the report

### Requirement: Stability under perturbation
The audit SHALL report how much the output changes under small parameter changes, seeded ball dropout
and slot permutation, as the share of frames and of spells that change.

#### Scenario: Parameter change
- **WHEN** each tunable parameter moves by its declared small step
- **THEN** the report gives the changed-frame and changed-spell share per parameter

#### Scenario: Slot permutation
- **WHEN** slots are permuted
- **THEN** zero frames change, or the audit fails

### Requirement: Audit is diagnostic, not a target
Audit outputs SHALL support review and rule decisions. They MUST NOT be optimised as a score, and MUST
NOT be committed when produced from the competition match.

#### Scenario: Output location
- **WHEN** the audit writes its report on the competition match
- **THEN** the report goes to an ignored local path and the human shares only the aggregate summary

#### Scenario: Synthetic run in CI
- **WHEN** CI runs the audit on a synthetic match
- **THEN** it completes without match assets
