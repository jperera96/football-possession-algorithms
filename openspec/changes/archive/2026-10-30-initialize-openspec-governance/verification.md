# Verification

## Status

Status: COMPLETE

## Tests Executed

All commands below were run on 2026-10-30 on macOS (Darwin 25.6.0) with Python 3.11.14 (scratch
virtualenv outside the repository), OpenSpec 1.13.1 and Node 20.19.0.

- `python -m unittest discover -s tests/governance -v` → `Ran 66 tests ... OK` (0 failures,
  0 errors, 0 skipped; the OpenSpec CLI test ran because `openspec` is installed).
- End-to-end bootstrap on a scratch clone (`git clone` of this repository, working tree copied,
  one local commit on branch `bootstrap`, base `main` = 5e094e2):
  `python tools/governance/check_openspec.py --base main --head HEAD --base-ref-name main --trusted-ref main --run-openspec`
  → `governance: PASS [bootstrap (initialize-openspec-governance)]`.
- Same clone, after fast-forwarding `main` to the bootstrap commit, using the base copy of the
  checker exactly as CI does:
  - code change without a declared change → exit 1, "implementation changes need an approved OpenSpec change";
  - `--mode audit --rev main --run-openspec` → `PASS [audit]`, "0 active and 1 archived change(s) checked".
- Before the evidence was written, the same bootstrap check failed (exit 1) on the template
  `verification.md`, listing every empty section and every uncovered requirement.
- Official validator on six synthetic CSVs generated outside the repository
  (`evaluation/validate_submission.py <file>`): valid file with lower-case labels → `OK`, exit 0;
  199,318 rows → `row count 199318 != 199319`; repeated frame → `'frame' column is not 0..199318 in order`;
  label `Q` → `labels outside ['H', 'A', 'D', 'X']: ['Q']`; blank cell → `empty label in 1 rows; write X to abstain`;
  header `f,l` → `could not read: expected columns 'frame' and 'label'`; all failures exit 1.

## Requirement Coverage

- Specification before implementation: `test_python_change_without_specification`, `test_ci_change_without_specification`, `test_dependency_change_without_specification`, `test_agents_md_change_without_specification`, `test_implementation_with_its_own_unapproved_spec`, `test_nonexistent_change_reference`, `test_already_archived_change_cannot_be_reused`; scratch-clone post-bootstrap check.
- Approval provenance: `test_fake_approval_markers_are_ignored`, `test_untrusted_base_branch`, `test_base_not_on_trusted_ref`, `test_renaming_an_approved_change_into_a_new_id`.
- Pull request classification: `test_valid_specification_pr_passes`, `test_evidence_only_update_is_implementation`, `test_implementation_smuggling_a_second_spec`, `test_unresolvable_base_fails_closed`, `test_empty_diff_cannot_be_classified`, `test_unexpected_path_characters`, `test_symlink_is_rejected`, `test_malformed_change_folder_name`, `test_malformed_and_ambiguous_change_ids`, `test_partial_governance_in_base_fails_closed`.
- Planning artifact completeness: `test_empty_proposal`, `test_template_placeholders_only`, `test_missing_design`, `test_tasks_without_design_or_tasks_file`, `test_tasks_missing_traceability_fields`, `test_invalid_delta_spec`, `test_specs_omitted_without_skip_specs`, `test_wrong_schema_and_missing_scope`, `test_overbroad_scope_pattern`, `test_algorithm_proposal_needs_algorithm_review`, `test_templates_carry_every_section_the_checker_requires`.
- Approved scope: `test_unapproved_scope_expansion`, `test_renaming_code_out_of_scope`, `test_glob_cannot_authorise_governance_paths`, `test_governance_policy_change_without_approved_scope`, `test_deleting_the_governance_checker`, `test_deleting_openspec_files`, `test_algorithm_code_under_non_algorithm_proposal`, `test_approved_task_text_cannot_be_rewritten`, `test_approved_design_cannot_change_in_implementation`, `test_governance_change_with_explicit_scope_passes`.
- Verification evidence: `test_tasks_checked_without_evidence`, `test_verification_must_cover_every_requirement`, `test_complete_status_with_unchecked_tasks`, `test_spec_pr_cannot_mark_tasks_done_or_add_evidence`, `test_python_change_without_tests`, `test_partial_implementation_in_progress_passes`.
- Archive integrity: `test_completed_tasks_and_archive_pass`, `test_invalid_archive_incomplete_tasks_and_altered_proposal`, `test_malformed_archive_folder_name`, `test_audit_rejects_incomplete_archived_change`, `test_main_specs_cannot_be_edited_directly`, `test_audit_of_valid_main_passes`; real `openspec archive` output compared byte-for-byte with the active change.
- One-time bootstrap: `test_bootstrap_follows_narrow_procedure`, `test_bootstrap_cannot_touch_algorithms`, `test_bootstrap_cannot_carry_other_changes_or_deletions`, `test_bootstrap_requires_its_own_documented_change`, `test_bootstrap_cannot_recur_once_governed`; scratch-clone bootstrap PASS.
- Confidential data independence: the checker and all tests ran with `data/` containing only `data/README.md`; checker code only calls `git` and optionally `openspec` on `git archive` exports of `openspec/`.
- Submission file format: six synthetic CSV scenarios above against the unmodified official validator.

## Lint and Static Checks

- `ruff check --line-length 130 tools/governance tests/governance` (ruff 0.6.9) → `All checks passed!`
- `python -m compileall -q tools/governance tests/governance` run on the scratch clone → exit 0.
- Wiring test asserts the workflow has no `continue-on-error`, no `pull_request_target`, has a
  timeout, `contents: read`, `persist-credentials: false`, SHA-pinned actions and passes the PR
  body only through `env`.

## OpenSpec Validation

- `openspec schema validate pulse-governed` → `Schema 'pulse-governed' is valid`.
- `openspec validate initialize-openspec-governance --strict` (before archive) → valid.
- `openspec archive initialize-openspec-governance --yes` → 9 + 1 requirements added to
  `openspec/specs/development-governance` and `openspec/specs/submission-contract`.
- `openspec validate --all --strict --no-interactive` (after archive) → `2 passed, 0 failed`.

## Determinism

The checker's decision depends only on the two commits; running the bootstrap check twice on the
same scratch commit gave the same output. No outputs that affect predictions changed.

## Deviations

- `verification.md` is a template plus checker rule rather than a schema artifact (schema
  version 1 only supports artifacts and `apply`; see design.md).
- The expanded workflow profile was applied through a temporary `XDG_CONFIG_HOME`, leaving the
  user's global OpenSpec configuration (`profile: core`) unchanged.
- `bulk-archive` and `onboard` workflows were not installed (not needed).

## Known Limitations

- GitHub enforcement is NOT active: no branch protection on `main` (API 404) and rulesets are
  unavailable for this private repository on its current plan (API 403). Until an admin
  configures protection, `openspec-governance` is advisory.
- The workflow has not run on GitHub yet; its behaviour there is verified only by the local
  scratch-clone simulation and static tests.
- `.claude/settings.json` deny rules do not stop reads through Bash; Codex has no equivalent
  project-level deny list.
- The checker cannot prove that recorded evidence is truthful; CI re-runs the governance tests
  independently, and reviewers must check other claims.
- Existing defects are unchanged by design: `run_experiment.py --test-all` still always exits 0,
  `.agents/skills/possession-pipeline` still documents hardcoded kickoff frames, and
  `DEVELOPING.md` still claims a pre-installed git hook that does not exist.

## Residual Risks

- Anyone with admin rights can bypass protections; anyone with write access can push to `main`
  until protection exists.
- A PR with mixed intent can still be split dishonestly across PRs; human review remains essential.
- `openspec update` with the default core profile would remove four generated workflows.

## Confidential Data Statement

No private competition asset was opened, printed or sent to a model during this change: `data/`
contains only `data/README.md`; no video, ATD, homography, Smart Tagging, cache, prediction CSV or
derived log was read. Public competition documentation and repository source code were read; the
only submission files processed were synthetic CSVs generated in a scratch directory.
