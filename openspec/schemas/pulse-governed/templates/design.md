# Design

## Context

<!-- Current architecture and constraints. See proposal.md for motivation. -->

## Target Architecture

<!-- The architecture after the change. Add a Mermaid diagram for cross-module changes. -->

## Affected Components

<!-- Files/components and how each changes. Must stay inside affected_areas. -->

## Data Flow and Interfaces

<!-- Inputs, outputs, data contracts, interfaces; pseudocode when relevant. -->

## Decisions and Alternatives

<!-- Key decisions, alternatives, trade-offs. -->

## Dependencies

<!-- New/changed dependencies with rationale and pinned versions, or "None". -->

## Complexity and Performance

<!-- Time/memory expectations and how they were estimated. -->

## Reproducibility

<!-- Determinism, parameter provenance, cache invalidation, expected outputs. -->

## Testing Strategy

<!-- Tests per requirement; synthetic/public data only in CI. -->

## Security and Confidentiality

<!-- How private competition data stays out of prompts, logs, caches in git and cloud models. -->

## Compatibility

<!-- Effects on existing strategies, scripts, submissions and contributors. -->

## Rollback and Migration

<!-- How to revert; migration steps if any. -->

<!-- ALGORITHM CHANGES ONLY: keep the section below and answer every question.
     NON-ALGORITHM CHANGES: delete everything from "## Possession Engine Considerations" to the end. -->
## Possession Engine Considerations

### Temporal Alignment
<!-- video_frame = frame_id - 1; half boundaries; no off-by-one. -->

### Missing Observations
<!-- Behaviour when the ball or players are NaN (41% of graded frames). -->

### Geometric Assumptions
<!-- Pitch dimensions, orientation, coordinate normalisation; derived, not hardcoded per match. -->

### Inference Uncertainty
<!-- Confidence, abstention (X) policy and its spellF1 consequences. -->

### H/A/D/X Semantics
<!-- How each label is produced; graded vs ungraded frames. -->

### Segmentation Impact
<!-- Effect on spell count/duration and false splits. -->

### Smart Tagging Interaction
<!-- Which tags are used and how conflicts with tracking are resolved. -->

### Overfitting Risk
<!-- Why parameters are not tuned to the public 5 minutes or this match. -->

### Determinism
<!-- Sources of nondeterminism and how they are removed. -->
