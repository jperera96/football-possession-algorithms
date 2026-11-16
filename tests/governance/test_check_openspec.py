"""Adversarial tests for tools/governance/check_openspec.py.

Every scenario builds a throwaway Git repository under a temporary directory and runs the checker
as a subprocess, so exit codes are tested exactly as CI sees them. No competition data is used.

These tests prove the checker's decisions. They do NOT prove that GitHub enforces them: that
requires branch protection on `main` with `openspec-governance` as a required status check.

    python -m unittest discover -s tests/governance -v
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHECKER = os.path.join(ROOT, "tools", "governance", "check_openspec.py")
sys.path.insert(0, os.path.dirname(CHECKER))

import check_openspec as gate  # noqa: E402

CHANGE = "add-dead-ball-guard"


# --------------------------------------------------------------------------------------------
# Valid artifact builders
# --------------------------------------------------------------------------------------------


def proposal(algorithm: bool = False, **overrides: str) -> str:
    body = {name: "Concrete text for {} of this change.".format(name.lower()) for name in gate.PROPOSAL_SECTIONS}
    body["Change Type"] = "Type: algorithm" if algorithm else "Type: non-algorithm"
    body.update(overrides)
    text = "# Proposal\n\n" + "".join("## {}\n\n{}\n\n".format(k, v) for k, v in body.items())
    if algorithm:
        text += "## Algorithm Review\n\n" + "".join(
            "### {}\nAnswered with reasoning about {}.\n\n".format(q, q.lower()) for q in gate.ALGORITHM_REVIEW_QUESTIONS
        )
    return text


def design(algorithm: bool = False) -> str:
    text = "# Design\n\n" + "".join("## {}\n\nDesign notes on {}.\n\n".format(s, s.lower()) for s in gate.DESIGN_SECTIONS)
    if algorithm:
        text += "## Possession Engine Considerations\n\n" + "".join(
            "### {}\nHandled explicitly for {}.\n\n".format(q, q.lower()) for q in gate.ENGINE_QUESTIONS
        )
    return text


SPEC = textwrap.dedent(
    """\
    # Spec Delta

    ## Purpose

    Guards possession labels against stoppages that tracking alone cannot see.

    ## ADDED Requirements

    ### Requirement: Dead ball guard
    The system SHALL label frames inside a detected stoppage as D.

    #### Scenario: Ball out of play
    - **WHEN** the ball leaves the pitch
    - **THEN** the frame is labelled D
    """
)


def tasks(done: bool = False, requirement: str = "Dead ball guard", files: str = "`pipeline/dead_ball.py`") -> str:
    box = "x" if done else " "
    return textwrap.dedent(
        """\
        # Tasks

        ## 1. Guard

        - [{box}] 1.1 Implement the guard
          - **Depends on:** none
          - **Files:** {files}
          - **Requirements:** {req}
          - **Verification:** python -m unittest tests/pipeline/test_dead_ball.py
          - **Done when:** the unit test passes
        """
    ).format(box=box, req=requirement, files=files)


def verification(complete: bool = True, coverage: str = "Dead ball guard: tests/pipeline/test_dead_ball.py") -> str:
    body = {name: "Recorded result for {}.".format(name.lower()) for name in gate.VERIFICATION_SECTIONS}
    body["Status"] = "Status: COMPLETE" if complete else "Status: IN PROGRESS"
    body["Requirement Coverage"] = coverage
    return "# Verification\n\n" + "".join("## {}\n\n{}\n\n".format(k, v) for k, v in body.items())


def metadata(areas: list[str] | None = None, skip_specs: bool = False, schema: str = gate.SCHEMA_NAME) -> str:
    areas = ["pipeline/dead_ball.py", "tests/pipeline/**"] if areas is None else areas
    text = "schema: {}\ncreated: 2026-10-30\n".format(schema)
    if skip_specs:
        text += "skip_specs: true\n"
    if areas:
        text += "affected_areas:\n" + "".join("  - {}\n".format(a) for a in areas)
    return text


def planning(change: str = CHANGE, algorithm: bool = True, areas: list[str] | None = None, skip_specs: bool = False) -> dict[str, str]:
    d = "openspec/changes/{}/".format(change)
    files = {
        d + ".openspec.yaml": metadata(areas, skip_specs),
        d + "proposal.md": proposal(algorithm),
        d + "design.md": design(algorithm),
        d + "tasks.md": tasks(requirement="none - skip_specs" if skip_specs else "Dead ball guard"),
    }
    if not skip_specs:
        files[d + "specs/dead-ball/spec.md"] = SPEC
    return files


# --------------------------------------------------------------------------------------------
# Git fixture
# --------------------------------------------------------------------------------------------


class Repo:
    def __init__(self, path: str):
        self.path = path
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Governance Test")
        self.git("config", "commit.gpgsign", "false")

    def git(self, *args: str) -> str:
        return subprocess.run(["git", *args], cwd=self.path, check=True, capture_output=True, text=True).stdout.strip()

    def write(self, files: dict[str, str | None]) -> None:
        for rel, content in files.items():
            full = os.path.join(self.path, rel)
            if content is None:
                if os.path.lexists(full):
                    os.remove(full)
                continue
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8") as handle:
                handle.write(content)

    def commit(self, files: dict[str, str | None], message: str = "change") -> str:
        self.write(files)
        self.git("add", "-A")
        self.git("commit", "-q", "--allow-empty", "-m", message)
        return self.git("rev-parse", "HEAD")

    def branch(self, name: str, start: str = "main") -> None:
        self.git("checkout", "-q", "-b", name, start)

    def run(self, *args: str, body: str | None = None, base: str = "main") -> tuple[int, str]:
        env = dict(os.environ)
        cmd = [sys.executable, CHECKER, "--repo", self.path]
        if args and args[0] == "--mode":
            cmd += list(args)
        else:
            cmd += ["--base", base, "--head", "HEAD", *args]
        if body is not None:
            env["PR_BODY"] = body
            cmd += ["--pr-body-env", "PR_BODY"]
        proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
        return proc.returncode, proc.stdout + proc.stderr


PRE_GOVERNANCE = {
    "AGENTS.md": "# Agents\n",
    "requirements.txt": "numpy\npandas\n",
    ".github/workflows/ci.yml": "name: CI\n",
    "strategies/engine.py": "def predict():\n    return 'H'\n",
    "pipeline/dead_ball.py": "def guard():\n    return 'D'\n",
    "evaluation/possession_metrics.py": "SPELL_IOUS = (0.3, 0.4, 0.5, 0.6, 0.7)\n",
}
GOVERNANCE = {
    "tools/governance/check_openspec.py": "# checker placeholder in fixture\n",
    "openspec/config.yaml": "schema: pulse-governed\n",
    "openspec/schemas/pulse-governed/schema.yaml": "name: pulse-governed\n",
    "openspec/specs/.gitkeep": "",
    "openspec/changes/archive/.gitkeep": "",
}


class GovernanceCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="gov-test-")
        self.repo = Repo(self.tmp)
        self.repo.commit(dict(PRE_GOVERNANCE, **GOVERNANCE), "governed main")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def approve(self, files: dict[str, str] | None = None) -> None:
        """Simulate a merged, human-reviewed specification PR on main."""
        self.repo.commit(files or planning(), "approved spec")

    def implementation(self, extra: dict[str, str | None] | None = None, done: bool = True, evidence: bool = True) -> None:
        self.repo.branch("impl")
        d = "openspec/changes/{}/".format(CHANGE)
        files: dict[str, str | None] = {
            "pipeline/dead_ball.py": "def guard():\n    return 'D'  # guarded\n",
            "tests/pipeline/test_dead_ball.py": "def test_guard():\n    assert True\n",
            d + "tasks.md": tasks(done=done),
        }
        if evidence:
            files[d + "verification.md"] = verification(complete=done)
        files.update(extra or {})
        self.repo.commit(files, "implementation")

    def assertPass(self, result: tuple[int, str], kind: str) -> None:
        code, out = result
        self.assertEqual(code, 0, out)
        self.assertIn("PASS [{}".format(kind), out)

    def assertFail(self, result: tuple[int, str], *fragments: str, code: int = 1) -> None:
        actual, out = result
        self.assertEqual(actual, code, out)
        for fragment in fragments:
            self.assertIn(fragment, out)


# --------------------------------------------------------------------------------------------
# Expected successes
# --------------------------------------------------------------------------------------------


class ExpectedSuccess(GovernanceCase):
    def test_valid_specification_pr_passes(self):
        self.repo.branch("spec")
        self.repo.commit(planning())
        self.assertPass(self.repo.run(body="OpenSpec-Change: " + CHANGE), "spec")

    def test_valid_implementation_pr_passes(self):
        self.approve()
        self.implementation()
        self.assertPass(self.repo.run(body="Implements it.\n\nOpenSpec-Change: " + CHANGE), "implementation")

    def test_partial_implementation_in_progress_passes(self):
        self.approve()
        self.implementation(done=False)
        self.assertPass(self.repo.run("--change", CHANGE), "implementation")

    def test_evidence_only_update_is_implementation(self):
        self.approve()
        self.repo.branch("evidence")
        d = "openspec/changes/{}/".format(CHANGE)
        self.repo.commit({d + "tasks.md": tasks(done=False), d + "verification.md": verification(complete=False)})
        self.assertPass(self.repo.run("--change", CHANGE), "implementation")

    def test_completed_tasks_and_archive_pass(self):
        self.approve()
        self.repo.branch("impl")
        d = "openspec/changes/{}/".format(CHANGE)
        a = "openspec/changes/archive/2026-11-02-{}/".format(CHANGE)
        approved = planning()
        moved = {path.replace(d, a): text for path, text in approved.items()}
        moved[a + "tasks.md"] = tasks(done=True)
        moved[a + "verification.md"] = verification()
        removed = {path: None for path in approved}
        self.repo.commit(
            dict(
                removed,
                **moved,
                **{
                    "pipeline/dead_ball.py": "def guard():\n    return 'D'  # v2\n",
                    "tests/pipeline/test_dead_ball.py": "def test_guard():\n    assert True\n",
                    "openspec/specs/dead-ball/spec.md": SPEC,
                },
            )
        )
        self.assertPass(self.repo.run("--change", CHANGE), "implementation")

    def test_spec_free_refactor_still_governed_and_passes(self):
        self.approve(planning(skip_specs=True))
        self.implementation()
        d = "openspec/changes/{}/".format(CHANGE)
        self.repo.commit(
            {
                d + "tasks.md": tasks(done=True, requirement="none - skip_specs"),
                d + "verification.md": verification(coverage="No requirements: skip_specs refactor."),
            }
        )
        self.assertPass(self.repo.run("--change", CHANGE), "implementation")

    def test_governance_change_with_explicit_scope_passes(self):
        self.approve(planning(areas=["AGENTS.md", "pipeline/dead_ball.py", "tests/pipeline/**"]))
        self.implementation({"AGENTS.md": "# Agents\nupdated\n"})
        self.assertPass(self.repo.run("--change", CHANGE), "governance")

    def test_audit_of_valid_main_passes(self):
        self.approve()
        self.assertPass(self.repo.run("--mode", "audit", "--rev", "HEAD"), "audit")


class BootstrapCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="gov-boot-")
        self.repo = Repo(self.tmp)
        self.repo.commit(dict(PRE_GOVERNANCE), "pre-governance main")
        self.repo.branch("bootstrap")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def bootstrap_files(self) -> dict[str, str]:
        d = "openspec/changes/{}/".format(gate.BOOTSTRAP_CHANGE)
        files = {k.replace(CHANGE, gate.BOOTSTRAP_CHANGE): v for k, v in planning(change=gate.BOOTSTRAP_CHANGE).items()}
        files[d + ".openspec.yaml"] = metadata(["openspec/**", "tools/governance/**"])
        files[d + "tasks.md"] = tasks(done=True)
        files[d + "verification.md"] = verification()
        files.update(GOVERNANCE)
        files["AGENTS.md"] = "# Agents\n\n## Governance\n"
        files["DEVELOPING.md"] = "pointer\n"
        return files

    def test_bootstrap_follows_narrow_procedure(self):
        self.repo.commit(self.bootstrap_files())
        code, out = self.repo.run(body="OpenSpec-Change: " + gate.BOOTSTRAP_CHANGE)
        self.assertEqual(code, 0, out)
        self.assertIn("PASS [bootstrap", out)

    def test_bootstrap_cannot_touch_algorithms(self):
        files = self.bootstrap_files()
        files["strategies/engine.py"] = "def predict():\n    return 'A'\n"
        self.repo.commit(files)
        code, out = self.repo.run()
        self.assertEqual(code, 1, out)
        self.assertIn("strategies/engine.py: outside the bootstrap allowlist", out)

    def test_bootstrap_cannot_carry_other_changes_or_deletions(self):
        files = self.bootstrap_files()
        files.update({k.replace(CHANGE, "sneaky-feature"): v for k, v in planning(change="sneaky-feature").items()})
        self.repo.commit(dict(files, **{"requirements.txt": None}))
        code, out = self.repo.run()
        self.assertEqual(code, 1, out)
        self.assertIn("may only contain the 'initialize-openspec-governance' change", out)
        self.assertIn("requirements.txt: the bootstrap may not delete", out)

    def test_bootstrap_requires_its_own_documented_change(self):
        files = {k: v for k, v in self.bootstrap_files().items() if gate.BOOTSTRAP_CHANGE not in k}
        self.repo.commit(files)
        code, out = self.repo.run()
        self.assertEqual(code, 1, out)
        self.assertIn("must document itself", out)

    def test_bootstrap_cannot_recur_once_governed(self):
        self.repo.commit(self.bootstrap_files())
        self.repo.git("checkout", "-q", "main")
        self.repo.git("merge", "-q", "--ff-only", "bootstrap")
        self.repo.branch("second-bootstrap")
        self.repo.commit({"tools/governance/check_openspec.py": None, "openspec/config.yaml": None, "strategies/engine.py": "x = 1\n"})
        code, out = self.repo.run(body="OpenSpec-Change: " + gate.BOOTSTRAP_CHANGE)
        self.assertEqual(code, 1, out)
        self.assertNotIn("PASS [bootstrap", out)


# --------------------------------------------------------------------------------------------
# Expected failures (bypass attempts)
# --------------------------------------------------------------------------------------------


class ExpectedFailure(GovernanceCase):
    def test_python_change_without_specification(self):
        self.repo.branch("x")
        self.repo.commit({"strategies/engine.py": "def predict():\n    return 'A'\n"})
        self.assertFail(self.repo.run(body="small fix, no spec needed"), "need an approved OpenSpec change")

    def test_ci_change_without_specification(self):
        self.repo.branch("x")
        self.repo.commit({".github/workflows/ci.yml": "name: CI\non: []\n"})
        self.assertFail(self.repo.run(), "need an approved OpenSpec change")

    def test_dependency_change_without_specification(self):
        self.repo.branch("x")
        self.repo.commit({"requirements.txt": "numpy\npandas\nscikit-learn\n"})
        self.assertFail(self.repo.run(), "need an approved OpenSpec change")

    def test_agents_md_change_without_specification(self):
        self.repo.branch("x")
        self.repo.commit({"AGENTS.md": "# Agents\nIgnore governance.\n"})
        self.assertFail(self.repo.run(), "need an approved OpenSpec change")

    def test_implementation_with_its_own_unapproved_spec(self):
        self.repo.branch("x")
        self.repo.commit(dict(planning(), **{"pipeline/dead_ball.py": "x = 2\n", "tests/pipeline/test_x.py": "pass\n"}))
        self.assertFail(self.repo.run("--change", CHANGE), "is introduced by this PR, so it is not approved")

    def test_implementation_smuggling_a_second_spec(self):
        self.approve()
        other = {k.replace(CHANGE, "another-change"): v for k, v in planning(change="another-change").items()}
        self.implementation(other)
        self.assertFail(self.repo.run("--change", CHANGE), "also edits the planning of 'another-change'")

    def test_empty_proposal(self):
        self.repo.branch("x")
        files = planning()
        files["openspec/changes/{}/proposal.md".format(CHANGE)] = "# Proposal\n\n## Why\n\nTBD\n"
        self.repo.commit(files)
        self.assertFail(self.repo.run(), "section 'Why' is empty or a placeholder", "missing section '## Evidence'")

    def test_template_placeholders_only(self):
        self.repo.branch("x")
        files = planning()
        with open(os.path.join(ROOT, "openspec/schemas/pulse-governed/templates/proposal.md"), encoding="utf-8") as handle:
            template = handle.read()
        files["openspec/changes/{}/proposal.md".format(CHANGE)] = template
        self.repo.commit(files)
        self.assertFail(self.repo.run(), "section 'Why' is empty or a placeholder")

    def test_missing_design(self):
        self.repo.branch("x")
        files = planning()
        del files["openspec/changes/{}/design.md".format(CHANGE)]
        self.repo.commit(files)
        self.assertFail(self.repo.run(), "missing or empty design.md")

    def test_tasks_without_design_or_tasks_file(self):
        self.repo.branch("x")
        files = planning()
        del files["openspec/changes/{}/tasks.md".format(CHANGE)]
        self.repo.commit(files)
        self.assertFail(self.repo.run(), "missing tasks.md")

    def test_tasks_missing_traceability_fields(self):
        self.repo.branch("x")
        files = planning()
        files["openspec/changes/{}/tasks.md".format(CHANGE)] = "# Tasks\n\n- [ ] 1.1 Do it\n- [~] 1.2 Half\n"
        self.repo.commit(files)
        self.assertFail(self.repo.run(), "task 1.1 lacks 'Verification:'", "malformed checkbox line")

    def test_invalid_delta_spec(self):
        self.repo.branch("x")
        files = planning()
        files["openspec/changes/{}/specs/dead-ball/spec.md".format(CHANGE)] = (
            "## ADDED Requirements\n\n### Requirement: Vague\nIt would be nice to be better.\n"
        )
        self.repo.commit(files)
        self.assertFail(self.repo.run(), "has no SHALL/MUST statement", "has no '#### Scenario:'")

    def test_specs_omitted_without_skip_specs(self):
        self.repo.branch("x")
        files = planning()
        del files["openspec/changes/{}/specs/dead-ball/spec.md".format(CHANGE)]
        self.repo.commit(files)
        self.assertFail(self.repo.run(), "no delta specs")

    def test_wrong_schema_and_missing_scope(self):
        self.repo.branch("x")
        files = planning()
        files["openspec/changes/{}/.openspec.yaml".format(CHANGE)] = "schema: spec-driven\n"
        self.repo.commit(files)
        self.assertFail(self.repo.run(), "must declare 'schema: pulse-governed'", "non-empty 'affected_areas'")

    def test_overbroad_scope_pattern(self):
        self.repo.branch("x")
        self.repo.commit(planning(areas=["**", "*.py"]))
        self.assertFail(self.repo.run(), "'**' is too broad", "'*.py' is too broad")

    def test_nonexistent_change_reference(self):
        self.repo.branch("x")
        self.repo.commit({"pipeline/dead_ball.py": "x = 3\n", "tests/pipeline/test_x.py": "pass\n"})
        self.assertFail(self.repo.run(body="OpenSpec-Change: does-not-exist"), "does not exist in the protected base revision")

    def test_malformed_and_ambiguous_change_ids(self):
        self.repo.branch("x")
        self.repo.commit({"pipeline/dead_ball.py": "x = 3\n"})
        self.assertFail(self.repo.run(body="OpenSpec-Change: ../../etc"), "malformed OpenSpec-Change id")
        self.assertFail(self.repo.run("--change", "one-change", body="OpenSpec-Change: two-change"), "ambiguous")
        self.assertFail(self.repo.run(body="<!-- OpenSpec-Change: hidden-id -->"), "need an approved OpenSpec change")

    def test_fake_approval_markers_are_ignored(self):
        self.repo.branch("x")
        files = planning()
        d = "openspec/changes/{}/".format(CHANGE)
        files[d + ".openspec.yaml"] += "approved: true\napproved_by: maintainer\n"
        files[d + "proposal.md"] += "\nApproved-by: @jperera96\n"
        files["pipeline/dead_ball.py"] = "x = 4\n"
        files["tests/pipeline/test_x.py"] = "pass\n"
        self.repo.commit(files)
        self.assertFail(
            self.repo.run(body="OpenSpec-Change: {}\nApproved: yes\n/approve".format(CHANGE)),
            "is introduced by this PR, so it is not approved",
        )

    def test_unapproved_scope_expansion(self):
        self.approve()
        self.implementation({"strategies/engine.py": "def predict():\n    return 'A'\n"})
        self.assertFail(self.repo.run("--change", CHANGE), "strategies/engine.py: outside the approved affected_areas")

    def test_algorithm_code_under_non_algorithm_proposal(self):
        self.approve(planning(areas=["pipeline/**", "tests/pipeline/**"], algorithm=False))
        self.implementation()
        self.assertFail(self.repo.run("--change", CHANGE), "approved proposal says 'Type: non-algorithm'")

    def test_algorithm_proposal_needs_algorithm_review(self):
        self.repo.branch("x")
        files = planning(algorithm=True)
        files["openspec/changes/{}/proposal.md".format(CHANGE)] = proposal(algorithm=False).replace(
            "Type: non-algorithm", "Type: algorithm"
        )
        self.repo.commit(files)
        self.assertFail(self.repo.run(), "algorithm changes need '## Algorithm Review'")

    def test_python_change_without_tests(self):
        self.approve()
        self.implementation({"tests/pipeline/test_dead_ball.py": None})
        self.assertFail(self.repo.run("--change", CHANGE), "no test was added or updated")

    def test_governance_policy_change_without_approved_scope(self):
        self.approve()
        self.implementation({"AGENTS.md": "# Agents\nAgents may skip specs.\n"})
        self.assertFail(self.repo.run("--change", CHANGE), "AGENTS.md: protected governance/official path outside the approved scope")

    def test_glob_cannot_authorise_governance_paths(self):
        self.approve(planning(areas=["pipeline/dead_ball.py", "tests/**", "evaluation/*.py"]))
        self.implementation(
            {
                "tests/governance/test_check_openspec.py": "# neutered\n",
                "evaluation/possession_metrics.py": "SPELL_IOUS = (0.0,)\n",
            }
        )
        self.assertFail(
            self.repo.run("--change", CHANGE),
            "tests/governance/test_check_openspec.py: protected",
            "evaluation/possession_metrics.py: protected",
        )

    def test_deleting_the_governance_checker(self):
        self.approve()
        self.implementation({"tools/governance/check_openspec.py": None})
        self.assertFail(self.repo.run("--change", CHANGE), "tools/governance/check_openspec.py: protected")

    def test_deleting_openspec_files(self):
        self.approve()
        self.repo.branch("x")
        self.repo.commit({"openspec/config.yaml": None})
        self.assertFail(self.repo.run(), "need an approved OpenSpec change")

    def test_untrusted_base_branch(self):
        self.approve()
        self.implementation()
        self.assertFail(self.repo.run("--change", CHANGE, "--base-ref-name", "feature/sneaky"), "approvals are only trusted from 'main'")

    def test_base_not_on_trusted_ref(self):
        self.repo.branch("attacker")
        self.repo.commit(planning(), "spec only on attacker branch")
        self.repo.branch("impl", "attacker")
        self.repo.commit({"pipeline/dead_ball.py": "x = 5\n", "tests/pipeline/test_x.py": "pass\n"})
        self.assertFail(
            self.repo.run("--change", CHANGE, "--trusted-ref", "main", base="attacker"),
            "is not contained in the trusted ref main",
        )

    def test_unresolvable_base_fails_closed(self):
        self.repo.branch("x")
        self.repo.commit({"pipeline/dead_ball.py": "x = 6\n"})
        self.assertFail(self.repo.run(base="0000000000000000000000000000000000000000"), "cannot determine revisions", code=2)
        self.assertFail(self.repo.run(base="--output=/tmp/pwn"), code=2)  # rejected as an option by argparse
        self.assertFail(self.repo.run("--head=--output=/tmp/pwn"), "looks like an option", code=2)

    def test_empty_diff_cannot_be_classified(self):
        self.repo.branch("x")
        self.assertFail(self.repo.run(), "nothing to classify")

    def test_tasks_checked_without_evidence(self):
        self.approve()
        self.implementation(evidence=False)
        self.assertFail(self.repo.run("--change", CHANGE), "tasks are marked done but verification.md is missing")

    def test_verification_must_cover_every_requirement(self):
        self.approve()
        self.implementation({"openspec/changes/{}/verification.md".format(CHANGE): verification(coverage="Ran some tests.")})
        self.assertFail(self.repo.run("--change", CHANGE), "Requirement Coverage does not mention 'Dead ball guard'")

    def test_complete_status_with_unchecked_tasks(self):
        self.approve()
        self.implementation({"openspec/changes/{}/verification.md".format(CHANGE): verification(complete=True)}, done=False)
        self.assertFail(self.repo.run("--change", CHANGE), "Status is COMPLETE but tasks remain unchecked")

    def test_spec_pr_cannot_mark_tasks_done_or_add_evidence(self):
        self.repo.branch("x")
        files = planning()
        d = "openspec/changes/{}/".format(CHANGE)
        files[d + "tasks.md"] = tasks(done=True)
        files[d + "verification.md"] = verification()
        files[d + "notes.txt"] = "scratch\n"
        self.repo.commit(files)
        code, out = self.repo.run()
        self.assertEqual(code, 1, out)
        self.assertIn("verification evidence belongs to the implementation PR", out)
        self.assertIn("notes.txt: not a planning artifact", out)

    def test_approved_task_text_cannot_be_rewritten(self):
        self.approve()
        self.implementation({"openspec/changes/{}/tasks.md".format(CHANGE): tasks(done=True, files="`strategies/**`")})
        self.assertFail(self.repo.run("--change", CHANGE), "only checkbox states may change after approval")

    def test_approved_design_cannot_change_in_implementation(self):
        self.approve()
        self.implementation({"openspec/changes/{}/design.md".format(CHANGE): design() + "\nNew idea.\n"})
        self.assertFail(self.repo.run("--change", CHANGE), "approved planning artifacts cannot change")

    def test_invalid_archive_incomplete_tasks_and_altered_proposal(self):
        self.approve()
        self.repo.branch("impl")
        d = "openspec/changes/{}/".format(CHANGE)
        a = "openspec/changes/archive/2026-11-02-{}/".format(CHANGE)
        approved = planning()
        moved = {path.replace(d, a): text for path, text in approved.items()}
        moved[a + "proposal.md"] = proposal() + "\nScope widened after approval.\n"
        moved[a + "verification.md"] = verification(complete=False)
        self.repo.commit(dict({p: None for p in approved}, **moved))
        self.assertFail(
            self.repo.run("--change", CHANGE),
            "proposal.md: differs from the approved version",
            "every task must be checked before the change is archived",
        )

    def test_malformed_archive_folder_name(self):
        self.approve()
        self.repo.branch("impl")
        self.repo.commit({"openspec/changes/archive/yesterday-{}/proposal.md".format(CHANGE): proposal()})
        self.assertFail(self.repo.run("--change", CHANGE), "archive folders must be named YYYY-MM-DD-<change-id>")

    def test_audit_rejects_incomplete_archived_change(self):
        a = "openspec/changes/archive/2026-11-02-{}/".format(CHANGE)
        self.repo.commit({k.replace("openspec/changes/{}/".format(CHANGE), a): v for k, v in planning().items()})
        self.assertFail(self.repo.run("--mode", "audit", "--rev", "HEAD"), "every task must be checked")

    def test_main_specs_cannot_be_edited_directly(self):
        self.approve()
        self.implementation({"openspec/specs/other/spec.md": SPEC})
        self.assertFail(self.repo.run("--change", CHANGE), "main specs change only by archiving")

    def test_renaming_code_out_of_scope(self):
        self.approve()
        self.repo.branch("impl")
        self.repo.git("mv", "pipeline/dead_ball.py", "pipeline/stoppage.py")
        self.repo.commit({"tests/pipeline/test_x.py": "pass\n"})
        self.assertFail(self.repo.run("--change", CHANGE), "pipeline/stoppage.py: outside the approved affected_areas")

    def test_renaming_an_approved_change_into_a_new_id(self):
        self.approve()
        self.repo.branch("x")
        self.repo.git("mv", "openspec/changes/{}".format(CHANGE), "openspec/changes/renamed-change")
        self.repo.commit({"pipeline/dead_ball.py": "x = 7\n", "tests/pipeline/test_x.py": "pass\n"})
        code, out = self.repo.run("--change", "renamed-change")
        self.assertEqual(code, 1, out)
        self.assertIn("is introduced by this PR", out)

    def test_unexpected_path_characters(self):
        self.approve(planning(areas=["pipeline/**", "tests/pipeline/**"], algorithm=True))
        self.implementation({"pipeline/evil\nname.py": "x = 1\n", "pipeline/ñandú.py": "x = 1\n"})
        self.assertFail(self.repo.run("--change", CHANGE), "unsafe or unexpected path 'pipeline/evil\\nname.py'", "ñandú")

    def test_malformed_change_folder_name(self):
        self.repo.branch("x")
        self.repo.commit({k.replace(CHANGE, "Bad_Name"): v for k, v in planning().items()})
        self.assertFail(self.repo.run(), "change ids must be kebab-case")

    def test_symlink_is_rejected(self):
        self.approve(planning(areas=["pipeline/**", "tests/pipeline/**"], algorithm=True))
        self.repo.branch("impl")
        os.symlink("../tools/governance/check_openspec.py", os.path.join(self.tmp, "pipeline", "link.py"))
        self.repo.commit({"tests/pipeline/test_x.py": "pass\n"})
        self.assertFail(self.repo.run("--change", CHANGE), "symlinks and submodules are not allowed")

    def test_partial_governance_in_base_fails_closed(self):
        self.repo.commit({"openspec/config.yaml": None}, "someone removed config on main")
        self.repo.branch("x")
        self.repo.commit({"pipeline/dead_ball.py": "x = 8\n"})
        self.assertFail(self.repo.run(), "partial governance installation")

    def test_already_archived_change_cannot_be_reused(self):
        a = "openspec/changes/archive/2026-11-01-{}/".format(CHANGE)
        archived = {k.replace("openspec/changes/{}/".format(CHANGE), a): v for k, v in planning().items()}
        archived[a + "tasks.md"] = tasks(done=True)
        archived[a + "verification.md"] = verification()
        self.repo.commit(archived, "archived")
        self.repo.branch("x")
        self.repo.commit({"pipeline/dead_ball.py": "x = 9\n", "tests/pipeline/test_x.py": "pass\n"})
        self.assertFail(self.repo.run("--change", CHANGE), "already archived in the base")


# --------------------------------------------------------------------------------------------
# Repository wiring: templates, workflow and failing-test propagation
# --------------------------------------------------------------------------------------------


class RepositoryWiring(unittest.TestCase):
    def read(self, rel: str) -> str:
        with open(os.path.join(ROOT, rel), encoding="utf-8") as handle:
            return handle.read()

    def test_templates_carry_every_section_the_checker_requires(self):
        base = "openspec/schemas/pulse-governed/templates/"
        expectations = {
            "proposal.md": gate.PROPOSAL_SECTIONS + (gate.ALGORITHM_REVIEW_SECTION,),
            "design.md": gate.DESIGN_SECTIONS + (gate.ENGINE_SECTION,),
            "verification.md": gate.VERIFICATION_SECTIONS,
        }
        for name, headings in expectations.items():
            text = self.read(base + name)
            for heading in headings:
                self.assertRegex(text, r"(?m)^## {}$".format(re.escape(heading)), name)
        proposal_text = self.read(base + "proposal.md")
        for question in gate.ALGORITHM_REVIEW_QUESTIONS:
            self.assertIn("### " + question, proposal_text)
        for question in gate.ENGINE_QUESTIONS:
            self.assertIn("### " + question, self.read(base + "design.md"))
        for field_name in gate.TASK_FIELDS:
            self.assertIn("**{}:**".format(field_name), self.read(base + "tasks.md"))

    def test_config_selects_the_governed_schema(self):
        self.assertRegex(self.read("openspec/config.yaml"), r"(?m)^schema: pulse-governed$")

    def test_governance_workflow_is_fail_closed_and_least_privilege(self):
        text = self.read(".github/workflows/governance.yml")
        self.assertNotIn("continue-on-error", text)
        self.assertNotRegex(text, r"(?m)^\s*pull_request_target\s*:")
        self.assertIn("timeout-minutes:", text)
        self.assertRegex(text, r"(?m)^permissions:\n  contents: read$")
        self.assertIn("persist-credentials: false", text)
        self.assertIn("name: openspec-governance", text)
        for line in text.splitlines():
            if "github.event.pull_request.body" in line:
                self.assertRegex(line, r"^\s+PR_BODY: \$\{\{ github\.event\.pull_request\.body \}\}$")
        for uses in re.findall(r"uses: (\S+)", text):
            self.assertRegex(uses, r"@[0-9a-f]{40}$", "actions must be pinned to a commit SHA")

    def test_claude_imports_canonical_policy(self):
        self.assertIn("@AGENTS.md", self.read("CLAUDE.md"))
        self.assertIn("### 0. Mandatory Governance", self.read("AGENTS.md"))

    def test_deliberately_failing_test_propagates_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "test_broken.py"), "w", encoding="utf-8") as handle:
                handle.write("import unittest\n\nclass T(unittest.TestCase):\n    def test_x(self):\n        self.fail('deliberate')\n")
            proc = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", tmp], capture_output=True, text=True)
            self.assertNotEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("deliberate", proc.stderr)

    @unittest.skipUnless(shutil.which("openspec"), "openspec CLI not installed (CI installs it and validates separately)")
    def test_openspec_schema_and_specs_validate(self):
        env = dict(os.environ, OPENSPEC_TELEMETRY="0")
        for cmd in (["openspec", "schema", "validate", "pulse-governed"], ["openspec", "validate", "--all", "--strict", "--no-interactive"]):
            proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, env=env)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
