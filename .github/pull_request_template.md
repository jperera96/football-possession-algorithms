<!--
Every PR is either a SPECIFICATION PR (planning for one OpenSpec change, nothing else) or an
IMPLEMENTATION PR (references a change already approved on main). See docs/OPEN_SPEC_WORKFLOW.md.
Replace <change-id> below; the governance check reads this line. Do not paste private match data.
-->

OpenSpec-Change: <change-id>

## PR type
- [ ] Specification PR — only `openspec/changes/<change-id>/` planning artifacts
- [ ] Implementation PR — the change above is already merged on `main`
- [ ] Governance change — implementation PR touching protected paths named in the approved `affected_areas`

## Summary
<!-- What and why, in two or three sentences. -->

## Verification
<!-- Commands actually run and their results. Implementation PRs: point to verification.md. -->

## Reviewer checklist
- [ ] **Requirements**: specs describe observable behaviour with SHALL/MUST and WHEN/THEN scenarios
- [ ] **Scope**: changed files match `affected_areas`; no silent scope expansion
- [ ] **Design**: decisions, alternatives, risks and rollback are credible
- [ ] **Testing**: tests cover each requirement; CI `openspec-governance` is green
- [ ] **Compliance**: no public-GT tuning, no match-specific frames/spells/teams/sides, no human event data for BAR-ATH
- [ ] **Reproducibility**: deterministic, no hidden cache, parameter provenance stated
- [ ] **Confidentiality**: no private assets, derived caches, predictions or logs added or quoted
- [ ] **Approval provenance**: implementation references a change that existed on `main` before this PR
