# Proposal

## Why

<!-- What problem are we solving and why does it matter now? -->

## Current Behavior

<!-- What the system does today, with file references. Label anything not verifiable without private data as UNVERIFIED. -->

## Desired Behavior

<!-- Observable behaviour after the change. -->

## What Changes

<!-- Bullet list of concrete changes. Mark breaking changes with **BREAKING**. -->

## Capabilities

### New Capabilities
<!-- `<capability-path>`: description. Each becomes specs/<capability-path>/spec.md -->

### Modified Capabilities
<!-- `<existing-capability-path>`: which requirement changes. Leave empty if none. -->

## Change Type

<!-- Exactly one line. `algorithm` = anything that can change the submitted labels. -->
Type: non-algorithm

## Alternatives Considered

<!-- Options rejected and why this approach was chosen. -->

## Out of Scope

<!-- What this change explicitly does not do. -->

## Affected Modules

<!-- Modules/files affected. Must agree with affected_areas in .openspec.yaml. -->

## Expected Benefit

<!-- What improves, and how we will know. -->

## Risks

<!-- What could go wrong. -->

## Rollback

<!-- How to revert safely. -->

## Evidence

<!-- What supports this proposal (tests, literature, other games, audits). Public 5-minute GT scores are not evidence for tuning or selection. -->

<!-- ALGORITHM CHANGES ONLY: keep the section below and answer every question.
     NON-ALGORITHM CHANGES: delete everything from "## Algorithm Review" to the end. -->
## Algorithm Review

### Hypothesis
<!-- Which physical, statistical or temporal property is modelled? -->

### Evidence Beyond the Competition Match
<!-- What supports the hypothesis other than watching/scoring BAR-ATH? -->

### Simpler Alternatives
<!-- Could an existing component achieve this with less complexity? -->

### Evaluation Methodology
<!-- Which legally usable dataset and metrics (spellF1 first)? Never the public 5 minutes for selection. -->

### Ablation
<!-- How will we show the component adds value on its own? -->

### Failure Modes
<!-- Missing data, wrong team assignment, tracklet switches, interrupted play. -->

### Generalization
<!-- Would it work on another match, other teams, other field orientation? -->

### Reproducibility
<!-- Same inputs + environment => identical output? Parameter provenance? Caches? -->

### Complexity
<!-- Computational and maintenance cost versus expected gain. -->

### Falsification
<!-- Which result would make us reject and revert this approach? -->

### Expected spellF1 Impact
<!-- Expected direction/size and on which dataset it will be measured. -->

### Why This Is Not a Match-Specific Patch
<!-- No frame numbers, spells, teams or sides of the competition match encoded. -->
