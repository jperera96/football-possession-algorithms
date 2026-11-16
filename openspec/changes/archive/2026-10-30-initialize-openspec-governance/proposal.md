# Proposal

## Why

The repository has no change control. Seventeen commits in four days changed the production
engine directly on `main`, tuned against the public 5-minute ground truth and hardcoded
match-specific constants (audit of 2026-10-30), and the existing CI cannot fail
(`run_experiment.py --test-all` always exits 0). With the 17 November 2026 deadline and AI agents
writing most of the code, the team needs a mechanism that makes every change deliberate,
reviewed, reproducible and compliant before it lands, and that applies equally to Claude Code,
Codex and humans.

## Current Behavior

- No OpenSpec, no specifications, no PR template, no CODEOWNERS, no branch protection
  (`gh api .../branches/main/protection` → 404; rulesets → 403 "Upgrade to GitHub Pro or make
  this repository public").
- `.github/workflows/ci.yml` runs strategy self-tests that cannot fail, validates the official
  baseline CSVs and scores against the public ground truth; it never checks process.
- `AGENTS.md` and `.agents/skills/{mtah-eval,possession-pipeline}` give domain guidance but no
  approval rules; no `CLAUDE.md` or `.claude/` existed.
- `DEVELOPING.md` claims a pre-installed `.git/hooks/pre-commit`; none exists (UNVERIFIED on
  other clones, absent on this one).

## Desired Behavior

Every change goes through a specification PR (planning only) that a human approves by merging
to `main`, then an implementation PR that references the approved change, stays within its
approved file scope, records verification evidence and archives the change. A deterministic
checker enforces this in CI and fails closed. All agents receive the same canonical policy.

## What Changes

- Initialise OpenSpec 1.13.1 with Claude Code and Codex integrations (expanded workflows:
  explore, propose, new, continue, ff, apply, verify, sync, archive, update).
- Add project schema `pulse-governed` (fork of `spec-driven`): mandatory design, Algorithm
  Review and Possession Engine Considerations for algorithm changes, traceable tasks and a
  `verification.md` evidence template; set it as the default in `openspec/config.yaml` with
  project context, artifact rules and apply/archive guidance.
- Add `tools/governance/check_openspec.py` and 66 adversarial tests in `tests/governance/`.
- Add `.github/workflows/governance.yml` (required check `openspec-governance`), a PR template
  and a proposed `.github/CODEOWNERS`.
- Add a canonical governance section 0 to `AGENTS.md` (existing content preserved), `CLAUDE.md`
  importing it, `.claude/settings.json` denying reads of private assets, and
  `docs/OPEN_SPEC_WORKFLOW.md`; point `DEVELOPING.md` at them.
- Document existing behaviour as initial specs: `development-governance` (new, implemented here)
  and `submission-contract` (the official validator's existing rules).

## Capabilities

### New Capabilities
- `development-governance`: specification-first workflow, approval provenance, scope, evidence,
  archive integrity and fail-closed classification of pull requests.
- `submission-contract`: the CSV format the official validator accepts (existing behaviour).

### Modified Capabilities
None (no specifications existed).

## Change Type

Type: non-algorithm

## Alternatives Considered

- README-only policy: rejected; it has no consequences.
- Default `spec-driven` schema: rejected; design is optional there and it has no algorithm review
  or evidence artifact.
- Approval via a field in `.openspec.yaml` or a PR label: rejected; both are writable by the
  contributor or agent being judged. Approval is instead the presence of the planning in the
  protected base revision, which only a reviewed merge can produce.
- Running the PR's own checker in CI: rejected; a PR could weaken it. CI runs the base copy.
- `pull_request_target`: rejected; it runs with elevated tokens next to untrusted code.
- pytest/pyyaml dependencies: rejected for now; the checker and tests are stdlib-only so they run
  without installing anything into the project environment.

## Out of Scope

Any change to the possession engine, strategies, pipeline, scorer, baseline, submission outputs
or existing CI checks; fixing the audit's findings (each needs its own change); configuring
GitHub settings (requires an admin and a plan that supports protection on private repos).

## Affected Modules

Governance only: `openspec/`, `tools/governance/`, `tests/governance/`, `.github/`, `.claude/`,
`.agents/skills/openspec-*`, `AGENTS.md`, `CLAUDE.md`, `docs/OPEN_SPEC_WORKFLOW.md`,
`DEVELOPING.md`. No Python module under `strategies/`, `pipeline/`, `evaluation/` or `starter/`.

## Expected Benefit

Unreviewed, unspecified or out-of-scope changes become visible and blocked once branch protection
requires `openspec-governance`; agents get one consistent policy; reviewers get a checklist and
traceable evidence; compliance rules (public GT, hardcoded frames, confidentiality) are explicit.

## Risks

- Process overhead near the deadline → artifacts may be short; templates guide content.
- False rejections from strict parsing → fail messages name the exact fix; amendments go through
  a quick specification PR.
- Without branch protection the check is advisory → documented as REQUIRES HUMAN CONFIGURATION.
- `openspec update` with the core profile removes expanded workflows → documented procedure.

## Rollback

Revert the bootstrap merge commit (or delete the added files and the AGENTS.md section 0 and the
DEVELOPING.md note) and remove `openspec-governance` from required checks. No application code or
data depends on these files.

## Evidence

- Audit of 2026-10-30 (H-01..H-05): public-GT tuning, match-specific constants, cache
  irreproducibility, CI that cannot fail.
- RULES.md §1–3 and FAQ.md (public GT for sanity only; algorithmic labels; reproducibility;
  private data not to cloud LLMs).
- `openspec --version` = 1.13.1; `openspec schema validate pulse-governed` passes.
- `python -m unittest discover -s tests/governance` (66 tests) passes; see verification.md.
