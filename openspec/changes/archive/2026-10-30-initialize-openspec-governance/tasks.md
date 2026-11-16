# Tasks

## 1. OpenSpec initialisation

- [x] 1.1 Initialise OpenSpec 1.13.1 for Claude Code and Codex with the expanded workflow profile
  - **Depends on:** none
  - **Files:** `openspec/`, `.claude/commands/opsx/`, `.claude/skills/openspec-*`, `.agents/skills/openspec-*`
  - **Requirements:** Specification before implementation
  - **Verification:** `openspec --version`; list generated skills; `git diff HEAD -- AGENTS.md .agents/skills/mtah-eval .agents/skills/possession-pipeline` shows no removals
  - **Done when:** 10 workflows exist for both tools and pre-existing instructions are intact

- [x] 1.2 Fork `spec-driven` into `pulse-governed`, write templates and make it the default schema
  - **Depends on:** 1.1
  - **Files:** `openspec/schemas/pulse-governed/**`, `openspec/config.yaml`
  - **Requirements:** Planning artifact completeness
  - **Verification:** `openspec schema validate pulse-governed`; wiring test `test_templates_carry_every_section_the_checker_requires`
  - **Done when:** the schema validates and every checker-required heading exists in the templates

## 2. Enforcement

- [x] 2.1 Implement the governance checker
  - **Depends on:** 1.2
  - **Files:** `tools/governance/check_openspec.py`
  - **Requirements:** Specification before implementation, Approval provenance, Pull request classification, Approved scope, Verification evidence, Archive integrity, One-time bootstrap, Confidential data independence
  - **Verification:** `python -m unittest discover -s tests/governance -v`; `ruff check --line-length 130 tools/governance tests/governance`
  - **Done when:** all governance tests pass and ruff reports no findings

- [x] 2.2 Write adversarial governance tests on synthetic Git repositories
  - **Depends on:** 2.1
  - **Files:** `tests/governance/test_check_openspec.py`
  - **Requirements:** Specification before implementation, Approval provenance, Pull request classification, Planning artifact completeness, Approved scope, Verification evidence, Archive integrity, One-time bootstrap
  - **Verification:** each bypass in the brief has a test asserting exit code and message
  - **Done when:** 66 tests pass, including every expected failure

- [x] 2.3 Add the CI workflow, PR template and proposed CODEOWNERS
  - **Depends on:** 2.1
  - **Files:** `.github/workflows/governance.yml`, `.github/pull_request_template.md`, `.github/CODEOWNERS`
  - **Requirements:** Approval provenance, Confidential data independence
  - **Verification:** wiring test `test_governance_workflow_is_fail_closed_and_least_privilege`; end-to-end run of the base-copy checker on a scratch clone
  - **Done when:** workflow is pinned, least-privilege, fail-closed and the job is named `openspec-governance`

## 3. Policy and specifications

- [x] 3.1 Add canonical policy, Claude integration, confidentiality deny list and workflow docs
  - **Depends on:** 1.1
  - **Files:** `AGENTS.md`, `CLAUDE.md`, `.claude/settings.json`, `docs/OPEN_SPEC_WORKFLOW.md`, `DEVELOPING.md`
  - **Requirements:** Specification before implementation, Confidential data independence
  - **Verification:** `git diff HEAD -- AGENTS.md DEVELOPING.md` contains only additions; wiring test `test_claude_imports_canonical_policy`
  - **Done when:** both agents resolve to the same AGENTS.md policy and no previous line was removed

- [x] 3.2 Specify the governance workflow and the existing submission contract
  - **Depends on:** 2.2
  - **Files:** `openspec/changes/initialize-openspec-governance/specs/**`
  - **Requirements:** Submission file format, Planning artifact completeness
  - **Verification:** `openspec validate initialize-openspec-governance --strict`; six synthetic CSVs against `evaluation/validate_submission.py`
  - **Done when:** validation passes and each submission-contract scenario reproduces with the official validator

## 4. Verification and archive

- [x] 4.1 Verify end to end and archive the bootstrap change
  - **Depends on:** 2.3, 3.1, 3.2
  - **Files:** `openspec/changes/initialize-openspec-governance/verification.md`, `openspec/specs/**`, `openspec/changes/archive/**`
  - **Requirements:** One-time bootstrap, Archive integrity
  - **Verification:** bootstrap check on a scratch clone commit against the current `main` tip; `openspec archive initialize-openspec-governance --yes`; `--mode audit`
  - **Done when:** the checker reports PASS [bootstrap] and the audit passes after archiving
