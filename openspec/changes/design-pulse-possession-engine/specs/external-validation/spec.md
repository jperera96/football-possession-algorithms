# Spec Delta

## Purpose

Provide a legitimate way to compare and select methods without any ground truth or hand labels from
the provided game, and keep the strength of each claim explicit.

## ADDED Requirements

### Requirement: Authorised dataset register
Only datasets listed in a register with source, licence or usage terms, access method and known
limitations MAY be used, and they MUST concern other games.

#### Scenario: Unregistered dataset
- **WHEN** the benchmark is pointed at an unregistered dataset
- **THEN** it refuses to run

#### Scenario: Public data not vendored
- **WHEN** an external dataset is used
- **THEN** a script obtains it into an ignored path, and the data is not committed

### Requirement: Adapters target the internal contract
External games SHALL be converted to the same contracts used for the competition match, and the
adapter SHALL report quality differences.

#### Scenario: Adapter round trip
- **WHEN** a synthetic fixture in an external format is loaded
- **THEN** it passes contract validation with known frames and positions

### Requirement: Reference labels declare their uncertainty
Reference labels derived from events SHALL be versioned, SHALL state their construction rules, and
SHALL mark ambiguous intervals. They MUST NOT be described as equivalent to the organisers' ground truth.

#### Scenario: Unclear interval between events
- **WHEN** consecutive events do not determine possession
- **THEN** the interval is marked ambiguous, and sensitivity is reported with and without it

#### Scenario: Definition sensitivity
- **WHEN** a result is reported
- **THEN** it is shown for at least two reasonable reference-label variants

### Requirement: Corruption suite
The benchmark SHALL apply seeded, documented corruptions: ball dropout conditioned on context, tracklet
fragmentation and swaps, wrong team assignment, coordinate noise and synthetic tag errors.

#### Scenario: Seeded corruption
- **WHEN** a corruption runs twice with one seed
- **THEN** the outputs are identical

#### Scenario: Clean baseline
- **WHEN** corruption strength is zero
- **THEN** the data equals the adapter output

### Requirement: Claim levels are separate
Reports SHALL state each result's level: implementation correctness, synthetic robustness, external
reference performance, cross-game generalisation, or unknown private competition performance.

#### Scenario: Competition performance
- **WHEN** a report is produced
- **THEN** private competition performance is stated as unknown and no estimate is given

### Requirement: Statistical comparison
Comparisons SHALL use the official metric implementation, spellF1 first and macroF1 second, with
leave-one-game-out analysis, paired bootstrap intervals and comparison with the baselines.

#### Scenario: Reporting a difference
- **WHEN** two methods are compared
- **THEN** the report gives the paired difference, its 95% interval and the number of games and spells

### Requirement: Selection rule
A more complex method SHALL be adopted only if, on the pre-declared external suite, the lower bound of
the 95% paired interval of its spellF1 difference is above zero, the difference is at least 0.04, and no
corruption family shows a worse result beyond that same margin.

#### Scenario: Meets every condition
- **WHEN** all conditions hold
- **THEN** the method may become the default through a recorded decision

#### Scenario: Selected after the fact
- **WHEN** the suite or margin is changed after results are seen
- **THEN** the result is exploratory and cannot justify adoption

### Requirement: Component ablation
Each engine rule and new component SHALL be evaluated by switching it off in the benchmark.

#### Scenario: Rule without benefit
- **WHEN** a rule shows no benefit under ablation
- **THEN** a recorded decision removes or disables it, or states why it stays

### Requirement: Provided game excluded from selection
Benchmark code MUST NOT load the competition match or its public ground truth.

#### Scenario: Competition game requested
- **WHEN** the benchmark is pointed at the competition game
- **THEN** it refuses to run
