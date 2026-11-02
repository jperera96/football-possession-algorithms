# OpenSpec Workflow (PULSE governance)

**Rule: no approved specification → no implementation.** This applies to every change, made by
humans or by agents. The policy is `AGENTS.md` §0; this document is the procedure.

Tooling: OpenSpec `@fission-ai/openspec@1.13.1` (Node.js ≥ 20.19.0), project schema
`pulse-governed` (`openspec/schemas/pulse-governed/`), checker
`tools/governance/check_openspec.py` (Python 3.11, stdlib only), CI job `openspec-governance`.

## 1. The two-stage pull-request workflow

```mermaid
flowchart LR
  A[explore] --> B[propose: proposal, specs, design, tasks]
  B --> C[Specification PR]
  C -->|human review + merge to main| D[Approved change on main]
  D --> E[Implementation PR<br/>OpenSpec-Change: id]
  E --> F[tasks checked + verification.md]
  F --> G[archive: specs synced]
  G -->|human review + merge| H[Done]
  E -.->|material design error| B
```

| | Specification PR | Implementation PR |
|---|---|---|
| Contains | `openspec/changes/<id>/` planning only: `.openspec.yaml`, `proposal.md`, `specs/**/spec.md`, `design.md`, `tasks.md`, optional `README.md`, `supporting/**` | Code, tests, docs inside `affected_areas`; task checkboxes; `verification.md`; archive move + main spec sync |
| Must not contain | Any other file, `verification.md`, newly checked tasks | Edits to approved proposal/specs/design/task text, planning of any other change |
| Declares | Optional `OpenSpec-Change: <id>` (must match) | Mandatory `OpenSpec-Change: <id>` in the PR description |
| Approval | Human review, merge to `main` | Change must already exist on `main`; human review |

**Approval provenance** is checked against the base revision (tip of `main`), never against
anything in the PR. A change introduced in the same PR as its implementation is rejected.

### What needs a new specification PR during implementation

Stop implementing and open a specification PR when you discover that:
- the approved behaviour (specs) is wrong or incomplete;
- the design's approach must change (different algorithm, data flow, interface, dependency);
- you need files outside `affected_areas`, or a protected path not explicitly listed;
- risks, rollback or compliance assumptions in the proposal no longer hold.

Record under `verification.md → Deviations` (no re-approval) only details that stay inside the
approved behaviour, design and `affected_areas`: helper names, internal refactors of new code,
an extra test, a clearer error message.

## 2. New feature (step by step)

1. **Explore**: `/opsx:explore` (Claude) or `$openspec-explore` (Codex). No files change.
2. **Propose**: `/opsx:propose <idea>` or `/opsx:new <id>` then `/opsx:continue`
   (CLI: `openspec new change <id>`; `openspec instructions <artifact> --change <id>`).
   Set `affected_areas` in `openspec/changes/<id>/.openspec.yaml`, e.g.
   ```yaml
   schema: pulse-governed
   created: 2026-11-01
   affected_areas:
     - pipeline/dead_ball.py
     - tests/pipeline/**
   ```
   Patterns must start with a literal path. Protected paths (`openspec/`, `.github/`,
   `AGENTS.md`, `CLAUDE.md`, `.claude/`, `.agents/`, `tools/governance/`, `tests/governance/`,
   `docs/OPEN_SPEC_WORKFLOW.md`, `.gitignore`, `.pre-commit-config.yaml`, the official scorer,
   `starter/baseline.py`, `evaluation/gt/`) need a pattern rooted in them.
3. **Review locally**: `openspec validate <id> --strict` and `openspec status --change <id>`.
4. **Specification PR**: commit only `openspec/changes/<id>/`, open a PR with
   `OpenSpec-Change: <id>`.
5. **Approval**: a human (Code Owner for governance) reviews and merges. Agents never approve.
6. **Start implementation** on a new branch from the updated `main`. Confirm approval:
   `git fetch origin && git ls-tree -r --name-only origin/main openspec/changes/<id>/`.
7. **Implement**: `/opsx:apply` (`$openspec-apply-change`). Stay inside `affected_areas`. Add
   tests for each requirement; any `.py` change requires a test change.
8. **Verify**: run the tasks' verifications, then `/opsx:verify`. Check a task only after it
   passed. Fill `verification.md` from `openspec/schemas/pulse-governed/templates/verification.md`
   with real commands and results and every requirement name under *Requirement Coverage*.
9. **Archive** when every task is checked and `Status: COMPLETE`: `/opsx:archive` or
   `openspec archive <id> --yes` (`--skip-specs` for `skip_specs` changes). This moves the change
   to `openspec/changes/archive/YYYY-MM-DD-<id>/` and syncs `openspec/specs/`.
10. **Implementation PR** with `OpenSpec-Change: <id>`; CI must be green; human approval; merge.
    A change may be implemented over several PRs: archive only in the last one.

Before pushing, run the same check CI runs (commit first; it compares revisions):

```bash
python tools/governance/check_openspec.py --base origin/main --head HEAD --change <id> --run-openspec
```

## 3. Bug fix

Same process with short artifacts: proposal (why, current vs desired behaviour, rollback), a
MODIFIED or ADDED requirement with a scenario reproducing the bug, a design of a few lines, and
one or two tasks including a regression test. Emergencies are not an exception.

## 4. Refactoring, tooling and docs

Behaviour does not change, so set `skip_specs: true` in `.openspec.yaml` and omit `specs/`.
Proposal, design, tasks, specification-PR approval, verification and archive
(`openspec archive <id> --yes --skip-specs`) are still mandatory. **A spec-free delta is not an
approval-free change.**

## 5. Algorithm changes

Anything that can change submitted labels is `Type: algorithm` in the proposal (the checker
rejects changes to `strategies/`, `pipeline/`, `run_experiment.py` or `games.py` under a
non-algorithm proposal). The proposal must answer the Algorithm Review — hypothesis, evidence
beyond the competition match, simpler alternatives, evaluation methodology, ablation, failure
modes, generalization, reproducibility, complexity, falsification, expected spellF1 impact, and
why it is not a match-specific patch. The design must answer the Possession Engine
Considerations. Public 5-minute ground truth is a sanity check only; select and tune on
independent games. Evidence decides whether experimental work is kept or reverted.

## 6. Agents (Claude Code, Codex)

- **Discovery**: Claude Code loads `CLAUDE.md` (which imports `AGENTS.md`), slash commands from
  `.claude/commands/opsx/` and skills from `.claude/skills/openspec-*`. Codex reads `AGENTS.md`
  and skills from `.agents/skills/openspec-*` (invoked as `$openspec-propose`, etc.). The
  pre-existing skills `.agents/skills/mtah-eval` and `possession-pipeline` remain; `AGENTS.md` §0
  overrides them where they conflict.
- **Installed workflows** (OpenSpec 1.13.1, custom profile): `explore`, `propose`, `new`,
  `continue`, `ff`, `apply`, `verify`, `sync`, `archive`, `update`.
  Claude: `/opsx:<workflow>`. Codex: `$openspec-explore`, `$openspec-propose`,
  `$openspec-new-change`, `$openspec-continue-change`, `$openspec-ff-change`,
  `$openspec-apply-change`, `$openspec-verify-change`, `$openspec-sync-specs`,
  `$openspec-archive-change`, `$openspec-update-change`.
- **CLI** (terminal): `openspec list [--specs]`, `openspec show <id>`, `openspec status --change <id>`,
  `openspec instructions <artifact> --change <id>`, `openspec validate [<id>|--all] --strict`,
  `openspec schema validate pulse-governed`, `openspec archive <id> --yes`.
- Planning workflows stop at planning. `apply` refuses unless the change is on `origin/main`.

### Updating OpenSpec

`openspec update` with the default *core* profile **removes** `new`, `continue`, `ff` and
`verify`. Regenerate generated files only in an approved governance change, using a temporary
config instead of editing your global one:

```bash
mkdir -p /tmp/openspec-profile/openspec
printf '%s' '{"profile":"custom","delivery":"both","workflows":["propose","explore","new","continue","apply","update","ff","sync","archive","verify"]}' > /tmp/openspec-profile/openspec/config.json
XDG_CONFIG_HOME=/tmp/openspec-profile openspec update .
```

## 7. Server-side protection (required; configured by a repository admin)

The checker only has consequences if GitHub enforces it. On `main`
(Settings → Branches → Branch protection rule, or Rulesets):

1. Require a pull request before merging; require **1+ approvals**; **dismiss stale approvals**
   when new commits are pushed; **require review from Code Owners** (after confirming
   `.github/CODEOWNERS`); require approval of the most recent push by someone other than the pusher.
2. Require status checks to pass: **`openspec-governance`** (and the existing CI jobs); require
   branches to be up to date before merging.
3. Require conversation resolution.
4. **Do not allow bypassing** the above, including administrators.
5. Block force pushes; block deletion of `main`.
6. Actions → General → Workflow permissions: **Read repository contents** only; do **not** allow
   GitHub Actions to create or approve pull requests.
7. Grant agent/bot tokens the minimum scope (no admin; ideally no direct push to `main`).

Private repositories on GitHub Free cannot use branch protection or rulesets; the repository
must be on a paid plan or public for these settings to exist. Until they are active, the checks
are advisory: anyone with write access can still push to `main`.

## 8. Reviewer checklist

- **Requirements**: observable behaviour; SHALL/MUST; WHEN/THEN scenarios incl. edge and failure cases.
- **Scope**: `affected_areas` is minimal; protected paths listed explicitly; out-of-scope edits absent.
- **Design**: alternatives, trade-offs, dependencies, performance, rollback are credible.
- **Risks**: failure modes and residual risks are named, not hand-waved.
- **Testing**: each requirement has a test; `verification.md` reports commands that CI also ran.
- **Compliance**: no public-GT tuning or selection; no frame/spell/team/side constants; no human
  event data about BAR-ATH; labels algorithmic.
- **Reproducibility**: deterministic; parameters have provenance; no hidden cache.
- **Confidentiality**: nothing derived from private assets is committed or quoted.
- **Approval provenance**: the implementation's change was on `main` before the PR; it is not
  self-approved by the same agent or author.

## 9. Bootstrap exception (one time only)

The PR that introduced this system could not have an approved specification because the system
did not exist. It is documented as the change `initialize-openspec-governance`. The checker
accepts bootstrap mode **only** when the base revision has neither
`tools/governance/check_openspec.py` nor `openspec/config.yaml`, and only for governance files
plus `DEVELOPING.md`; it never authorises algorithm, data or tooling changes. Once merged, every
later change — including changes to governance itself — needs an approved specification.
