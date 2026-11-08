# Spec Delta

## Purpose

Give the team an out-of-sample measurement of the engine on other games, so that changes can be
selected without the competition match or its public ground truth.

## ADDED Requirements

### Requirement: Authorised dataset register
Only registered datasets of other games SHALL be used, each with source, usage terms, access method
and known limitations. Data SHALL be downloaded by script into an ignored path and MUST NOT be committed.

#### Scenario: Unregistered dataset
- **WHEN** the benchmark is pointed at an unregistered dataset
- **THEN** it refuses to run

#### Scenario: Competition game
- **WHEN** the benchmark is pointed at the competition game or its public ground truth
- **THEN** it refuses to run

### Requirement: Adapters target the engine's input
External games SHALL be converted into the same input structure the engine uses for the competition
match, together with a quality report covering ball availability, slot count and frame rate.

#### Scenario: Adapter fixture
- **WHEN** a small team-written fixture in an external format is loaded
- **THEN** the result has the expected frames, positions and teams

### Requirement: Reference labels declare their uncertainty
Reference H, A and D labels SHALL be derived from events by documented, versioned rules in at least two
variants, with ambiguous intervals marked. They MUST NOT be described as equivalent to the organisers'
ground truth.

#### Scenario: Ambiguous interval
- **WHEN** consecutive events do not determine possession
- **THEN** the interval is marked ambiguous, and results are reported with and without it

#### Scenario: Variant disagreement
- **WHEN** a conclusion differs in sign between reference variants
- **THEN** it is reported as sensitive to the definition and cannot justify adoption

### Requirement: Realistic corruption
The benchmark SHALL apply seeded corruptions at documented strengths: ball dropout up to the published
rate of the competition data, concentrated near duels and flights; tracklet fragmentation and swaps;
wrong team on segments; coordinate noise.

#### Scenario: Seeded run
- **WHEN** a corruption runs twice with one seed
- **THEN** the outputs are identical

#### Scenario: Zero strength
- **WHEN** corruption strength is zero
- **THEN** the data equals the adapter output

### Requirement: Comparable reporting
Results SHALL use the official metric functions, spellF1 first and macroF1 second. Each report SHALL
show per-game values, paired bootstrap 95% intervals and the baseline on the same data, and SHALL state
that the competition score is unknown.

#### Scenario: Report content
- **WHEN** two engine versions are compared
- **THEN** the report gives per-game and pooled differences with intervals, the baseline, corruption results and the claim that competition performance is unknown

### Requirement: Selection rule
A change SHALL become default only if, on the frozen suite, the lower bound of the paired 95% interval
of the spellF1 difference is above zero, both reference variants agree in sign, and no corruption family
is worse by more than 0.04. Otherwise the simpler option SHALL stay default.

#### Scenario: Inconclusive result
- **WHEN** the interval includes zero
- **THEN** the simpler option stays default

#### Scenario: Suite changed after results
- **WHEN** the suite or rule changes after candidate results are seen
- **THEN** the comparison is exploratory and cannot justify adoption
