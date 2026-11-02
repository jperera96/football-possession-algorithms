#!/usr/bin/env python3
"""OpenSpec governance gate: no approved specification, no implementation.

Classifies the change between a trusted base revision (the tip of the protected branch) and a
proposed head revision, and fails closed unless the change follows the two-stage workflow in
docs/OPEN_SPEC_WORKFLOW.md:

    bootstrap       the one-time OpenSpec initialization (only while the base has no governance)
    spec            planning artifacts for exactly one change, nothing else
    implementation  any other change; must reference a change already approved in the base
    governance      an implementation change that touches protected governance/official paths

Approval provenance is never read from the pull request. A change counts as approved only when
its planning artifacts already exist in the base revision, which reaches the protected branch
through a reviewed specification PR. Text in the PR body only *names* the change.

The checker reads Git objects and repository text files only. It never executes the possession
engine and never needs the private competition data.

    python tools/governance/check_openspec.py --base origin/main --head HEAD --change <id>
    python tools/governance/check_openspec.py --mode audit --rev HEAD

Exit status: 0 when every check passes, 1 when a policy check fails, 2 on usage or Git errors.
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field

SCHEMA_NAME = "pulse-governed"
BOOTSTRAP_CHANGE = "initialize-openspec-governance"
CHECKER_PATH = "tools/governance/check_openspec.py"
OPENSPEC_CONFIG = "openspec/config.yaml"
CHANGES_ROOT = "openspec/changes/"
ARCHIVE_ROOT = "openspec/changes/archive/"
MAIN_SPECS_ROOT = "openspec/specs/"

# Paths whose modification changes the rules themselves, the agents' instructions, CI, or the
# official competition assets. Implementation changes may touch them only when the approved
# change names them through an affected_areas entry rooted inside the protected path.
PROTECTED_FILES = (
    "AGENTS.md",
    "CLAUDE.md",
    ".gitignore",
    ".pre-commit-config.yaml",
    "evaluation/possession_metrics.py",
    "evaluation/validate_submission.py",
    "evaluation/run_evaluation.py",
    "starter/baseline.py",
)
PROTECTED_PREFIXES = (
    "openspec/",
    ".github/",
    ".claude/",
    ".agents/",
    "tools/governance/",
    "tests/governance/",
    "docs/governance/",
    "docs/OPEN_SPEC_WORKFLOW.md",
    "evaluation/gt/",
)
# Paths whose behaviour determines the submitted labels. A change touching them must declare
# itself an algorithm change, which makes the proposal's Algorithm Review mandatory.
ALGORITHM_PREFIXES = ("strategies/", "pipeline/", "run_experiment.py", "games.py")
# The only non-governance file the bootstrap may touch (to point contributors at the workflow).
BOOTSTRAP_EXTRA_FILES = ("DEVELOPING.md",)

CHANGE_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ARCHIVE_DIR_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})-([a-z0-9]+(?:-[a-z0-9]+)*)$")
SAFE_PATH_RE = re.compile(r"^[A-Za-z0-9_.@+-][A-Za-z0-9_.@+/ -]*$")
AREA_PATTERN_RE = re.compile(r"^[A-Za-z0-9_.@+*?-][A-Za-z0-9_.@+/*? -]*$")
DECLARATION_RE = re.compile(r"^[ \t>*_-]*OpenSpec-Change[ \t]*:[ \t]*(\S*)[ \t]*$", re.I | re.M)
CHANGE_TYPE_RE = re.compile(r"^Type:\s*(algorithm|non-algorithm)\s*$", re.M)
STATUS_RE = re.compile(r"^Status:\s*(COMPLETE|IN PROGRESS)\s*$", re.M)
TASK_RE = re.compile(r"^- \[( |x|X)\] (\d+(?:\.\d+)*) (\S.*)$")
ANY_CHECKBOX_RE = re.compile(r"^\s*[-*+]\s*\[[^\]]*\]")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
PLACEHOLDER_RE = re.compile(r"^(tbd|todo|tbc|tba|xxx|\.\.\.|-|none yet|<[^>]*>)$", re.I)

PROPOSAL_SECTIONS = (
    "Why",
    "Current Behavior",
    "Desired Behavior",
    "What Changes",
    "Capabilities",
    "Change Type",
    "Alternatives Considered",
    "Out of Scope",
    "Affected Modules",
    "Expected Benefit",
    "Risks",
    "Rollback",
    "Evidence",
)
ALGORITHM_REVIEW_SECTION = "Algorithm Review"
ALGORITHM_REVIEW_QUESTIONS = (
    "Hypothesis",
    "Evidence Beyond the Competition Match",
    "Simpler Alternatives",
    "Evaluation Methodology",
    "Ablation",
    "Failure Modes",
    "Generalization",
    "Reproducibility",
    "Complexity",
    "Falsification",
    "Expected spellF1 Impact",
    "Why This Is Not a Match-Specific Patch",
)
DESIGN_SECTIONS = (
    "Context",
    "Target Architecture",
    "Affected Components",
    "Data Flow and Interfaces",
    "Decisions and Alternatives",
    "Dependencies",
    "Complexity and Performance",
    "Reproducibility",
    "Testing Strategy",
    "Security and Confidentiality",
    "Compatibility",
    "Rollback and Migration",
)
ENGINE_SECTION = "Possession Engine Considerations"
ENGINE_QUESTIONS = (
    "Temporal Alignment",
    "Missing Observations",
    "Geometric Assumptions",
    "Inference Uncertainty",
    "H/A/D/X Semantics",
    "Segmentation Impact",
    "Smart Tagging Interaction",
    "Overfitting Risk",
    "Determinism",
)
TASK_FIELDS = ("Depends on", "Files", "Requirements", "Verification", "Done when")
VERIFICATION_SECTIONS = (
    "Status",
    "Tests Executed",
    "Requirement Coverage",
    "Lint and Static Checks",
    "OpenSpec Validation",
    "Determinism",
    "Deviations",
    "Known Limitations",
    "Residual Risks",
    "Confidential Data Statement",
)
PLANNING_FILES = (".openspec.yaml", "README.md", "proposal.md", "design.md", "tasks.md")
APPROVED_ARTIFACTS = (".openspec.yaml", "proposal.md", "design.md")


class GitError(Exception):
    """A Git command failed or a revision could not be resolved: the gate cannot decide."""


# --------------------------------------------------------------------------------------------
# Git access
# --------------------------------------------------------------------------------------------


class Repo:
    def __init__(self, root: str):
        self.root = root

    def git(self, *args: str, binary: bool = False) -> bytes | str:
        proc = subprocess.run(
            ["git", "-c", "core.quotepath=off", *args],
            cwd=self.root,
            capture_output=True,
        )
        if proc.returncode != 0:
            raise GitError(
                "git {} failed: {}".format(" ".join(args), proc.stderr.decode("utf-8", "replace").strip())
            )
        return proc.stdout if binary else proc.stdout.decode("utf-8")

    def ok(self, *args: str) -> bool:
        proc = subprocess.run(["git", *args], cwd=self.root, capture_output=True)
        return proc.returncode == 0

    def commit(self, rev: str) -> str:
        if rev.startswith("-"):
            raise GitError("refusing revision that looks like an option: {!r}".format(rev))
        return str(self.git("rev-parse", "--verify", "--quiet", rev + "^{commit}")).strip()

    def exists(self, rev: str, path: str) -> bool:
        return self.ok("cat-file", "-e", "{}:{}".format(rev, path))

    def read(self, rev: str, path: str) -> str | None:
        if not self.exists(rev, path):
            return None
        data = self.git("cat-file", "blob", "{}:{}".format(rev, path), binary=True)
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError as error:
            raise GitError("{} at {} is not UTF-8 text: {}".format(path, rev[:12], error)) from error

    def ls(self, rev: str, prefix: str) -> list[str]:
        out = self.git("ls-tree", "-r", "-z", "--name-only", rev, "--", prefix, binary=True)
        return [p.decode("utf-8") for p in out.split(b"\0") if p]


@dataclass
class Entry:
    status: str
    path: str
    new_mode: str


def diff_entries(repo: Repo, base: str, head: str) -> list[Entry]:
    out = repo.git("diff", "--raw", "-z", "--no-renames", "--no-ext-diff", base, head, binary=True)
    fields = out.split(b"\0")
    entries: list[Entry] = []
    i = 0
    while i < len(fields) and fields[i]:
        meta = fields[i].decode("utf-8")
        if i + 1 >= len(fields):
            raise GitError("truncated git diff output")
        path = fields[i + 1].decode("utf-8")
        parts = meta.lstrip(":").split()
        if len(parts) != 5:
            raise GitError("unparseable git diff record: {!r}".format(meta))
        entries.append(Entry(status=parts[4][0], path=path, new_mode=parts[1]))
        i += 2
    return entries


# --------------------------------------------------------------------------------------------
# Markdown and metadata parsing
# --------------------------------------------------------------------------------------------


def strip_comments(text: str) -> str:
    return COMMENT_RE.sub("", text)


def sections(text: str, level: int) -> dict[str, str]:
    """Map heading title -> body for headings of exactly `level`, body ending at the next heading
    of the same or a higher level. Fenced code blocks are ignored when looking for headings."""
    out: dict[str, str] = {}
    current: str | None = None
    body: list[str] = []
    fenced = False
    for line in strip_comments(text).splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
        match = None if fenced else HEADING_RE.match(line)
        if match and len(match.group(1)) <= level:
            if current is not None:
                out[current] = "\n".join(body)
            current = match.group(2).strip() if len(match.group(1)) == level else None
            body = []
            continue
        if current is not None:
            body.append(line)
    if current is not None:
        out[current] = "\n".join(body)
    return out


def substantive(body: str) -> bool:
    lines = []
    for raw in body.splitlines():
        line = raw.strip().lstrip("-*+>").strip()
        if line and not line.startswith("#"):
            lines.append(line)
    if not lines:
        return False
    text = " ".join(lines).strip()
    return len(re.findall(r"\w", text)) >= 3 and not PLACEHOLDER_RE.match(text)


def require_sections(text: str, names: tuple[str, ...], level: int, where: str, errors: list[str]) -> dict[str, str]:
    found = sections(text, level)
    for name in names:
        if name not in found:
            errors.append("{}: missing section '{} {}'".format(where, "#" * level, name))
        elif not substantive(found[name]):
            errors.append("{}: section '{}' is empty or a placeholder".format(where, name))
    return found


def parse_metadata(text: str, where: str, errors: list[str]) -> dict[str, object]:
    """Parse the flat subset of YAML that .openspec.yaml uses. Anything else fails closed."""
    data: dict[str, object] = {}
    key: str | None = None
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.split(" #", 1)[0].rstrip() if not raw.lstrip().startswith("#") else ""
        if not line.strip():
            continue
        item = re.match(r"^\s+-\s+(.*)$", line)
        if item and key is not None and isinstance(data.get(key), list):
            data[key].append(unquote(item.group(1)))  # type: ignore[union-attr]
            continue
        pair = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):(?:\s+(.*))?$", line)
        if not pair:
            errors.append("{}:{}: unsupported YAML syntax: {!r}".format(where, number, raw))
            continue
        key, value = pair.group(1), (pair.group(2) or "").strip()
        if key in data:
            errors.append("{}:{}: duplicate key '{}'".format(where, number, key))
        if value == "":
            data[key] = []
        elif value.startswith("["):
            if not value.endswith("]"):
                errors.append("{}:{}: unterminated inline list".format(where, number))
                continue
            inner = value[1:-1].strip()
            data[key] = [unquote(v) for v in inner.split(",")] if inner else []
        elif value in ("true", "false"):
            data[key] = value == "true"
        else:
            data[key] = unquote(value)
    return data


def unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        return value[1:-1]
    return value


def glob_match(pattern: str, path: str) -> bool:
    """Segment-wise glob: '**' spans any number of segments, '*' and '?' stay within one."""

    def walk(pp: list[str], sp: list[str]) -> bool:
        if not pp:
            return not sp
        if pp[0] == "**":
            return any(walk(pp[1:], sp[i:]) for i in range(len(sp) + 1))
        return bool(sp) and fnmatch.fnmatchcase(sp[0], pp[0]) and walk(pp[1:], sp[1:])

    return walk(pattern.split("/"), path.split("/"))


def literal_prefix(pattern: str) -> str:
    match = re.search(r"[*?]", pattern)
    return pattern if match is None else pattern[: match.start()]


def is_protected(path: str) -> bool:
    return path in PROTECTED_FILES or any(path.startswith(p) or path == p.rstrip("/") for p in PROTECTED_PREFIXES)


def roots_protected(pattern: str, path: str) -> bool:
    """A protected path is in scope only through a pattern whose literal part already names the
    protected area, so '**' or '*.md' can never silently authorise a governance edit."""
    prefix = literal_prefix(pattern)
    if not prefix:
        return False
    if prefix == path:
        return True
    return is_protected(prefix) or prefix in PROTECTED_FILES


def is_test_path(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    return path.startswith("tests/") or name.startswith("test_") or name.endswith("_test.py")


# --------------------------------------------------------------------------------------------
# Change artifacts
# --------------------------------------------------------------------------------------------


@dataclass
class Task:
    task_id: str
    done: bool
    text: str
    fields: dict[str, str] = field(default_factory=dict)


@dataclass
class ChangeInfo:
    change_id: str
    directory: str
    algorithm: bool = False
    skip_specs: bool = False
    areas: list[str] = field(default_factory=list)
    requirements: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    tasks: list[Task] = field(default_factory=list)
    has_verification: bool = False
    verification_complete: bool = False


def parse_tasks(text: str, where: str, errors: list[str]) -> list[Task]:
    tasks: list[Task] = []
    current: Task | None = None
    for raw in strip_comments(text).splitlines():
        match = TASK_RE.match(raw)
        if match:
            current = Task(task_id=match.group(2), done=match.group(1) != " ", text=match.group(3))
            tasks.append(current)
            continue
        if ANY_CHECKBOX_RE.match(raw):
            errors.append("{}: malformed checkbox line {!r} (use '- [ ] N.M description')".format(where, raw.strip()))
            continue
        if HEADING_RE.match(raw):
            current = None
            continue
        sub = re.match(r"^\s+[-*]\s+\**([A-Za-z ]+?)\**\s*:\s*\**\s*(.*)$", raw)
        if sub and current is not None:
            current.fields[sub.group(1).strip().lower()] = sub.group(2).strip()
    seen: set[str] = set()
    for task in tasks:
        if task.task_id in seen:
            errors.append("{}: duplicate task id {}".format(where, task.task_id))
        seen.add(task.task_id)
        for name in TASK_FIELDS:
            value = task.fields.get(name.lower(), "")
            if not value or PLACEHOLDER_RE.match(value):
                errors.append("{}: task {} lacks '{}:'".format(where, task.task_id, name))
    if not tasks:
        errors.append("{}: no tasks ('- [ ] 1.1 description')".format(where))
    return tasks


def normalise_tasks(text: str) -> str:
    lines = [TASK_RE.sub(lambda m: "- [ ] {} {}".format(m.group(2), m.group(3)), raw.rstrip()) for raw in text.splitlines()]
    return "\n".join(lines).strip()


def parse_spec(text: str, where: str, errors: list[str]) -> list[str]:
    """Structural check of a delta spec. Returns the requirement names it adds or modifies."""
    names: list[str] = []
    ops = sections(text, 2)
    delta_ops = [op for op in ops if re.match(r"^(ADDED|MODIFIED|REMOVED|RENAMED) Requirements$", op)]
    if not delta_ops:
        errors.append("{}: no '## ADDED|MODIFIED|REMOVED|RENAMED Requirements' section".format(where))
    for op in delta_ops:
        kind = op.split()[0]
        requirements = sections(ops[op], 3)
        blocks = {k: v for k, v in requirements.items() if k.startswith("Requirement:")}
        if not blocks and kind != "RENAMED":
            errors.append("{}: '{}' has no '### Requirement:' blocks".format(where, op))
        for title, body in blocks.items():
            name = title.split(":", 1)[1].strip()
            if not name:
                errors.append("{}: unnamed requirement".format(where))
                continue
            if kind == "REMOVED":
                if "**Reason**" not in body or "**Migration**" not in body:
                    errors.append("{}: removed requirement '{}' needs **Reason** and **Migration**".format(where, name))
                continue
            names.append(name)
            statement = re.split(r"^####", body, maxsplit=1, flags=re.M)[0]
            if not re.search(r"\b(SHALL|MUST)\b", statement):
                errors.append("{}: requirement '{}' has no SHALL/MUST statement".format(where, name))
            scenarios = re.split(r"^#### Scenario:", body, flags=re.M)[1:]
            if not scenarios:
                errors.append("{}: requirement '{}' has no '#### Scenario:'".format(where, name))
            for scenario in scenarios:
                if not re.search(r"\*\*WHEN\*\*", scenario) or not re.search(r"\*\*THEN\*\*", scenario):
                    errors.append("{}: a scenario of '{}' lacks **WHEN**/**THEN**".format(where, name))
        if kind == "RENAMED":
            for target in re.findall(r"^\s*-?\s*TO:\s*`?###\s*Requirement:\s*(.+?)`?\s*$", ops[op], re.M):
                names.append(target.strip())
    return names


def check_change(
    repo: Repo,
    rev: str,
    directory: str,
    change_id: str,
    errors: list[str],
    *,
    require_verification: bool = False,
) -> ChangeInfo:
    """Validate the planning artifacts of one change as they exist at `rev`."""
    info = ChangeInfo(change_id=change_id, directory=directory)
    where = "{}@{}".format(directory.rstrip("/"), rev[:12])
    files = repo.ls(rev, directory)
    if not files:
        errors.append("{}: change directory does not exist".format(where))
        return info

    meta_text = repo.read(rev, directory + ".openspec.yaml")
    if meta_text is None:
        errors.append("{}: missing .openspec.yaml".format(where))
        meta: dict[str, object] = {}
    else:
        meta = parse_metadata(meta_text, where + "/.openspec.yaml", errors)
    if meta.get("schema") != SCHEMA_NAME:
        errors.append("{}: .openspec.yaml must declare 'schema: {}' (found {!r})".format(where, SCHEMA_NAME, meta.get("schema")))
    info.skip_specs = meta.get("skip_specs") is True
    areas = meta.get("affected_areas")
    if not isinstance(areas, list) or not areas:
        errors.append("{}: .openspec.yaml needs a non-empty 'affected_areas' list (the approved file scope)".format(where))
    else:
        for pattern in areas:
            if not AREA_PATTERN_RE.match(pattern) or ".." in pattern.split("/") or pattern.startswith("/"):
                errors.append("{}: unsafe affected_areas pattern {!r}".format(where, pattern))
            elif not literal_prefix(pattern) or pattern.strip("*/?") == "":
                errors.append("{}: affected_areas pattern {!r} is too broad".format(where, pattern))
            else:
                info.areas.append(pattern)

    proposal = repo.read(rev, directory + "proposal.md")
    if proposal is None or not proposal.strip():
        errors.append("{}: missing or empty proposal.md".format(where))
    else:
        found = require_sections(proposal, PROPOSAL_SECTIONS, 2, where + "/proposal.md", errors)
        kind = CHANGE_TYPE_RE.findall(strip_comments(found.get("Change Type", "")))
        if len(kind) != 1:
            errors.append("{}/proposal.md: 'Change Type' must contain exactly one line 'Type: algorithm' or 'Type: non-algorithm'".format(where))
        info.algorithm = kind == ["algorithm"]
        if info.algorithm:
            if ALGORITHM_REVIEW_SECTION not in found:
                errors.append("{}/proposal.md: algorithm changes need '## {}'".format(where, ALGORITHM_REVIEW_SECTION))
            else:
                require_sections(found[ALGORITHM_REVIEW_SECTION], ALGORITHM_REVIEW_QUESTIONS, 3, where + "/proposal.md", errors)

    design = repo.read(rev, directory + "design.md")
    if design is None or not design.strip():
        errors.append("{}: missing or empty design.md (mandatory for every change)".format(where))
    else:
        found = require_sections(design, DESIGN_SECTIONS, 2, where + "/design.md", errors)
        if info.algorithm:
            if ENGINE_SECTION not in found:
                errors.append("{}/design.md: algorithm changes need '## {}'".format(where, ENGINE_SECTION))
            else:
                require_sections(found[ENGINE_SECTION], ENGINE_QUESTIONS, 3, where + "/design.md", errors)

    spec_files = sorted(p for p in files if p.startswith(directory + "specs/"))
    for path in spec_files:
        if not path.endswith("/spec.md"):
            errors.append("{}: unexpected file in specs/: {}".format(where, path))
            continue
        info.capabilities.append(path[len(directory + "specs/") : -len("/spec.md")])
        info.requirements += parse_spec(repo.read(rev, path) or "", path, errors)
    if not spec_files and not info.skip_specs:
        errors.append("{}: no delta specs; add specs/<capability>/spec.md or set 'skip_specs: true'".format(where))
    if spec_files and info.skip_specs:
        errors.append("{}: 'skip_specs: true' but delta specs are present".format(where))

    tasks_text = repo.read(rev, directory + "tasks.md")
    if tasks_text is None:
        errors.append("{}: missing tasks.md".format(where))
    else:
        info.tasks = parse_tasks(tasks_text, where + "/tasks.md", errors)
        if not info.skip_specs:
            known = [r.lower() for r in info.requirements]
            for task in info.tasks:
                ref = task.fields.get("requirements", "").lower()
                if ref and not any(name in ref for name in known):
                    errors.append("{}/tasks.md: task {} references no requirement of this change".format(where, task.task_id))

    allowed = {directory + name for name in PLANNING_FILES + ("verification.md",)}
    for path in files:
        if path in allowed or path in spec_files or path.startswith(directory + "supporting/"):
            continue
        errors.append("{}: unexpected file {}".format(where, path))

    verification = repo.read(rev, directory + "verification.md")
    any_done = any(t.done for t in info.tasks)
    all_done = bool(info.tasks) and all(t.done for t in info.tasks)
    if verification is not None:
        info.has_verification = True
        check_verification(verification, info, where + "/verification.md", errors)
    elif any_done or require_verification:
        errors.append("{}: tasks are marked done but verification.md is missing".format(where))
    if require_verification and not all_done:
        errors.append("{}: every task must be checked before the change is archived".format(where))
    return info


def check_verification(text: str, info: ChangeInfo, where: str, errors: list[str]) -> None:
    found = require_sections(text, VERIFICATION_SECTIONS, 2, where, errors)
    status = STATUS_RE.findall(strip_comments(found.get("Status", "")))
    if len(status) != 1:
        errors.append("{}: 'Status' must contain exactly one line 'Status: COMPLETE' or 'Status: IN PROGRESS'".format(where))
        return
    info.verification_complete = status[0] == "COMPLETE"
    all_done = bool(info.tasks) and all(t.done for t in info.tasks)
    if info.verification_complete and not all_done:
        errors.append("{}: Status is COMPLETE but tasks remain unchecked".format(where))
    if all_done and not info.verification_complete:
        errors.append("{}: all tasks are checked but Status is not COMPLETE".format(where))
    coverage = strip_comments(found.get("Requirement Coverage", "")).lower()
    for name in info.requirements:
        if name.lower() not in coverage:
            errors.append("{}: Requirement Coverage does not mention '{}'".format(where, name))


# --------------------------------------------------------------------------------------------
# Classification and policy
# --------------------------------------------------------------------------------------------


@dataclass
class Classified:
    planning: dict[str, list[Entry]] = field(default_factory=dict)
    archive: dict[str, list[Entry]] = field(default_factory=dict)
    main_specs: list[Entry] = field(default_factory=list)
    protected: list[Entry] = field(default_factory=list)
    implementation: list[Entry] = field(default_factory=list)


def classify(entries: list[Entry], errors: list[str]) -> Classified:
    out = Classified()
    for entry in entries:
        path = entry.path
        if path.startswith(ARCHIVE_ROOT) and path.count("/") >= 4:
            folder = path[len(ARCHIVE_ROOT) :].split("/", 1)[0]
            match = ARCHIVE_DIR_RE.match(folder)
            if not match:
                errors.append("{}: archive folders must be named YYYY-MM-DD-<change-id>".format(path))
                continue
            out.archive.setdefault(match.group(4) + "@" + folder, []).append(entry)
        elif path.startswith(CHANGES_ROOT) and not path.startswith(ARCHIVE_ROOT) and path.count("/") >= 3:
            change_id = path[len(CHANGES_ROOT) :].split("/", 1)[0]
            if not CHANGE_ID_RE.match(change_id) or not 3 <= len(change_id) <= 64:
                errors.append("{}: change ids must be kebab-case [a-z0-9-], 3-64 characters".format(path))
                continue
            out.planning.setdefault(change_id, []).append(entry)
        elif path.startswith(MAIN_SPECS_ROOT) and path != MAIN_SPECS_ROOT + ".gitkeep":
            out.main_specs.append(entry)
        elif is_protected(path):
            out.protected.append(entry)
        else:
            out.implementation.append(entry)
    return out


def check_paths(entries: list[Entry], errors: list[str]) -> None:
    for entry in entries:
        path = entry.path
        segments = path.split("/")
        if not SAFE_PATH_RE.match(path) or "" in segments or "." in segments or ".." in segments or path.endswith(" "):
            errors.append("unsafe or unexpected path {!r}: rename it to [A-Za-z0-9._@+-/ ]".format(path))
        if entry.status not in ("A", "M", "D"):
            errors.append("{}: unsupported change type '{}' (type changes are not allowed)".format(path, entry.status))
        if entry.new_mode in ("120000", "160000"):
            errors.append("{}: symlinks and submodules are not allowed".format(path))


def declared_change(args: argparse.Namespace, errors: list[str]) -> str | None:
    found: set[str] = set()
    if args.change:
        found.add(args.change)
    if args.pr_body_env:
        body = strip_comments(os.environ.get(args.pr_body_env, ""))
        found.update(DECLARATION_RE.findall(body))
    if len(found) > 1:
        errors.append("ambiguous OpenSpec-Change declarations: {}".format(", ".join(sorted(found))))
        return None
    if not found:
        return None
    change_id = found.pop()
    if not CHANGE_ID_RE.match(change_id) or not 3 <= len(change_id) <= 64:
        errors.append("malformed OpenSpec-Change id {!r}".format(change_id))
        return None
    return change_id


def archived_folders(repo: Repo, rev: str, change_id: str) -> list[str]:
    folders = {p[len(ARCHIVE_ROOT) :].split("/", 1)[0] for p in repo.ls(rev, ARCHIVE_ROOT) if p.count("/") >= 4}
    return sorted(f for f in folders if (m := ARCHIVE_DIR_RE.match(f)) and m.group(4) == change_id)


def run_openspec(repo: Repo, rev: str, targets: list[str], errors: list[str]) -> None:
    """Run the official OpenSpec validator on an exported, read-only copy of `rev`."""
    binary = shutil.which("openspec")
    if binary is None:
        errors.append("--run-openspec was requested but the 'openspec' CLI is not installed")
        return
    with tempfile.TemporaryDirectory(prefix="openspec-gate-") as tmp:
        archive = repo.git("archive", "--format=tar", rev, "openspec", binary=True)
        subprocess.run(["tar", "-x", "-C", tmp], input=archive, check=True)
        env = dict(os.environ, OPENSPEC_TELEMETRY="0", DO_NOT_TRACK="1", CI="1")
        for target in targets:
            cmd = [binary, "validate", "--strict", "--no-interactive"] + target.split()
            proc = subprocess.run(cmd, cwd=tmp, capture_output=True, text=True, env=env)
            if proc.returncode != 0:
                detail = (proc.stdout + proc.stderr).strip().splitlines()[-12:]
                errors.append("openspec {} failed at {}:\n    {}".format(" ".join(cmd[1:]), rev[:12], "\n    ".join(detail)))


@dataclass
class Report:
    kind: str = "unclassified"
    change: str | None = None
    errors: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def check_bootstrap(repo: Repo, head: str, entries: list[Entry], declared: str | None, report: Report) -> None:
    report.kind = "bootstrap"
    report.change = BOOTSTRAP_CHANGE
    errors = report.errors
    if declared not in (None, BOOTSTRAP_CHANGE):
        errors.append("the bootstrap PR may only declare OpenSpec-Change: {}".format(BOOTSTRAP_CHANGE))
    for entry in entries:
        path = entry.path
        if entry.status == "D":
            errors.append("{}: the bootstrap may not delete existing files".format(path))
        in_bootstrap_change = path.startswith(CHANGES_ROOT + BOOTSTRAP_CHANGE + "/") or bool(
            path.startswith(ARCHIVE_ROOT)
            and (m := ARCHIVE_DIR_RE.match(path[len(ARCHIVE_ROOT) :].split("/", 1)[0]))
            and m.group(4) == BOOTSTRAP_CHANGE
        )
        other_change = (
            path.startswith(CHANGES_ROOT)
            and not in_bootstrap_change
            and path not in (CHANGES_ROOT + ".gitkeep", ARCHIVE_ROOT + ".gitkeep")
            and path.count("/") >= 3
        )
        if other_change:
            errors.append("{}: the bootstrap may only contain the '{}' change".format(path, BOOTSTRAP_CHANGE))
        elif not (in_bootstrap_change or is_protected(path) or path in BOOTSTRAP_EXTRA_FILES):
            errors.append("{}: outside the bootstrap allowlist (algorithms, data and tooling are not part of the bootstrap)".format(path))
    for required in (CHECKER_PATH, OPENSPEC_CONFIG, "openspec/schemas/{}/schema.yaml".format(SCHEMA_NAME)):
        if not repo.exists(head, required):
            errors.append("the bootstrap must add {}".format(required))
    active = CHANGES_ROOT + BOOTSTRAP_CHANGE + "/"
    folders = archived_folders(repo, head, BOOTSTRAP_CHANGE)
    if repo.ls(head, active):
        check_change(repo, head, active, BOOTSTRAP_CHANGE, errors, require_verification=True)
    elif len(folders) == 1:
        check_change(repo, head, ARCHIVE_ROOT + folders[0] + "/", BOOTSTRAP_CHANGE, errors, require_verification=True)
    else:
        errors.append("the bootstrap must document itself as the OpenSpec change '{}'".format(BOOTSTRAP_CHANGE))


def check_spec_pr(repo: Repo, base: str, head: str, change_id: str, entries: list[Entry], declared: str | None, report: Report) -> None:
    report.kind = "spec"
    report.change = change_id
    errors = report.errors
    if declared not in (None, change_id):
        errors.append("PR declares OpenSpec-Change: {} but only modifies the planning of '{}'".format(declared, change_id))
    directory = CHANGES_ROOT + change_id + "/"
    if archived_folders(repo, base, change_id):
        errors.append("'{}' was already archived; propose a new change id".format(change_id))
    if not repo.ls(head, directory):
        report.kind = "spec-withdrawal"
        base_info = check_change(repo, base, directory, change_id, [])
        if any(t.done for t in base_info.tasks):
            errors.append("'{}' has implemented tasks; it cannot be withdrawn by deleting its planning".format(change_id))
        return
    for entry in entries:
        name = entry.path[len(directory) :]
        if name == "verification.md":
            errors.append("{}: verification evidence belongs to the implementation PR, not the specification PR".format(entry.path))
        elif not (name in PLANNING_FILES or name.startswith("specs/") or name.startswith("supporting/")):
            errors.append("{}: not a planning artifact".format(entry.path))
    info = check_change(repo, head, directory, change_id, errors)
    base_done = set()
    if repo.ls(base, directory):
        base_done = {t.task_id for t in check_change(repo, base, directory, change_id, []).tasks if t.done}
    newly_done = sorted(t.task_id for t in info.tasks if t.done and t.task_id not in base_done)
    if newly_done:
        errors.append("a specification PR cannot mark tasks done: {}".format(", ".join(newly_done)))


def check_implementation_pr(
    repo: Repo, base: str, head: str, groups: Classified, declared: str | None, report: Report
) -> None:
    errors = report.errors
    report.kind = "governance" if groups.protected else "implementation"
    if declared is None:
        errors.append(
            "implementation changes need an approved OpenSpec change: add 'OpenSpec-Change: <id>' to the PR "
            "description (or pass --change). Planning goes in a separate specification PR first."
        )
        return
    report.change = declared
    directory = CHANGES_ROOT + declared + "/"
    if not repo.ls(base, directory):
        if archived_folders(repo, base, declared):
            errors.append("'{}' is already archived in the base; open a new change".format(declared))
        elif repo.ls(head, directory):
            errors.append("'{}' is introduced by this PR, so it is not approved; merge it through a specification PR first".format(declared))
        else:
            errors.append("'{}' does not exist in the protected base revision".format(declared))
        return

    approved_errors: list[str] = []
    approved = check_change(repo, base, directory, declared, approved_errors)
    for message in approved_errors:
        errors.append("approved planning is invalid: " + message)

    for change_id in groups.planning:
        if change_id != declared:
            errors.append("this PR also edits the planning of '{}': specifications are approved in their own PR".format(change_id))

    for entry in groups.planning.get(declared, []):
        name = entry.path[len(directory) :]
        if name == "verification.md" and entry.status in ("A", "M"):
            continue
        if name == "tasks.md" and entry.status == "M":
            before, after = repo.read(base, entry.path) or "", repo.read(head, entry.path) or ""
            if normalise_tasks(before) != normalise_tasks(after):
                errors.append("{}: only checkbox states may change after approval; reopen the specification PR".format(entry.path))
            continue
        if entry.status == "D" and groups.archive:
            continue  # moved by the archive step, verified below
        errors.append("{}: approved planning artifacts cannot change in an implementation PR".format(entry.path))

    archived_here = [k for k in groups.archive if k.split("@", 1)[0] == declared]
    for key in groups.archive:
        if key not in archived_here:
            errors.append("this PR touches the archived change '{}'".format(key.split("@", 1)[1]))
    if len(archived_here) > 1:
        errors.append("'{}' is archived more than once".format(declared))

    archiving = bool(archived_here)
    final_dir = directory
    if archiving:
        folder = archived_here[0].split("@", 1)[1]
        final_dir = ARCHIVE_ROOT + folder + "/"
        if repo.ls(head, directory):
            errors.append("{}: archived but the active directory still exists".format(directory))
        for name in APPROVED_ARTIFACTS:
            if repo.read(base, directory + name) != repo.read(head, final_dir + name):
                errors.append("{}{}: differs from the approved version".format(final_dir, name))
        for path in repo.ls(base, directory + "specs/"):
            if repo.read(base, path) != repo.read(head, final_dir + path[len(directory) :]):
                errors.append("{}: archived spec differs from the approved version".format(path))
        if normalise_tasks(repo.read(base, directory + "tasks.md") or "") != normalise_tasks(repo.read(head, final_dir + "tasks.md") or ""):
            errors.append("{}tasks.md: only checkbox states may differ from the approved version".format(final_dir))
    elif not repo.ls(head, directory):
        errors.append("{}: the approved change was deleted without being archived".format(directory))

    final = check_change(repo, head, final_dir, declared, errors, require_verification=True if archiving else False)
    if not final.has_verification:
        errors.append("{}verification.md: an implementation PR must record its verification evidence".format(final_dir))

    for entry in groups.main_specs:
        capability = entry.path[len(MAIN_SPECS_ROOT) :].rsplit("/", 1)[0]
        synced = archiving and capability in approved.capabilities and entry.path.endswith("/spec.md")
        explicit = any(glob_match(p, entry.path) and roots_protected(p, entry.path) for p in approved.areas)
        if not (synced or explicit):
            errors.append("{}: main specs change only by archiving a change that owns this capability".format(entry.path))

    for entry in groups.protected:
        if not any(glob_match(p, entry.path) and roots_protected(p, entry.path) for p in approved.areas):
            errors.append(
                "{}: protected governance/official path outside the approved scope (needs an explicit, "
                "path-rooted affected_areas entry approved in a specification PR)".format(entry.path)
            )

    for entry in groups.implementation:
        if not any(glob_match(p, entry.path) for p in approved.areas):
            errors.append("{}: outside the approved affected_areas; amend the scope in a specification PR".format(entry.path))
        if entry.path.startswith(ALGORITHM_PREFIXES) and not approved.algorithm:
            errors.append("{}: algorithmic code changed but the approved proposal says 'Type: non-algorithm'".format(entry.path))

    code = [e for e in groups.implementation + groups.protected if e.path.endswith(".py") and not is_test_path(e.path)]
    tests = [e for e in groups.implementation + groups.protected if is_test_path(e.path) and e.status in ("A", "M")]
    if code and not tests:
        errors.append("Python code changed ({}) but no test was added or updated".format(", ".join(e.path for e in code[:3])))


def check_pr(args: argparse.Namespace, repo: Repo) -> Report:
    report = Report()
    errors = report.errors
    if args.base_ref_name is not None and args.base_ref_name != args.protected_branch:
        errors.append("base branch is '{}', but approvals are only trusted from '{}'".format(args.base_ref_name, args.protected_branch))
        return report
    base = repo.commit(args.base)
    head = repo.commit(args.head)
    if args.trusted_ref:
        trusted = repo.commit(args.trusted_ref)
        if not repo.ok("merge-base", "--is-ancestor", base, trusted):
            errors.append("base {} is not contained in the trusted ref {}".format(base[:12], args.trusted_ref))
            return report
    merge_base = str(repo.git("merge-base", base, head)).strip()
    entries = diff_entries(repo, merge_base, head)
    if not entries:
        errors.append("no changes between base and head: nothing to classify")
        return report
    check_paths(entries, errors)
    declared = declared_change(args, errors)
    if errors:
        return report

    has_checker, has_config = repo.exists(base, CHECKER_PATH), repo.exists(base, OPENSPEC_CONFIG)
    if not has_checker and not has_config:
        check_bootstrap(repo, head, entries, declared, report)
        if args.run_openspec and not report.errors:
            run_openspec(repo, head, ["--all"], errors)
        return report
    if not (has_checker and has_config):
        errors.append("the base revision has a partial governance installation; refusing to decide")
        return report

    groups = classify(entries, errors)
    if errors:
        return report
    only_planning = len(groups.planning) == 1 and not (groups.archive or groups.main_specs or groups.protected or groups.implementation)
    if only_planning:
        # Evidence-only updates (verification.md plus task checkboxes) are implementation work.
        change_id = next(iter(groups.planning))
        touched = {e.path[len(CHANGES_ROOT + change_id) + 1 :] for e in groups.planning[change_id]}
        only_planning = not ("verification.md" in touched and touched <= {"verification.md", "tasks.md"})
    if only_planning:
        change_id = next(iter(groups.planning))
        check_spec_pr(repo, base, head, change_id, groups.planning[change_id], declared, report)
        if args.run_openspec and not report.errors and report.kind == "spec":
            run_openspec(repo, head, [change_id + " --type change"], errors)
    else:
        check_implementation_pr(repo, base, head, groups, declared, report)
        if args.run_openspec and not report.errors:
            run_openspec(repo, base, [report.change + " --type change"], errors)
            run_openspec(repo, head, ["--specs"], errors)
    return report


def audit(args: argparse.Namespace, repo: Repo) -> Report:
    """Validate every change at one revision (used on pushes to the protected branch)."""
    report = Report(kind="audit")
    rev = repo.commit(args.rev)
    if not repo.exists(rev, OPENSPEC_CONFIG):
        report.errors.append("{} is missing at {}".format(OPENSPEC_CONFIG, rev[:12]))
        return report
    paths = repo.ls(rev, CHANGES_ROOT)
    active = sorted({p.split("/")[2] for p in paths if not p.startswith(ARCHIVE_ROOT) and p.count("/") >= 3})
    archived = sorted({p.split("/")[3] for p in paths if p.startswith(ARCHIVE_ROOT) and p.count("/") >= 4})
    for change_id in active:
        if not CHANGE_ID_RE.match(change_id):
            report.errors.append("invalid change id folder {!r}".format(change_id))
            continue
        check_change(repo, rev, CHANGES_ROOT + change_id + "/", change_id, report.errors)
    for folder in archived:
        match = ARCHIVE_DIR_RE.match(folder)
        if not match:
            report.errors.append("invalid archive folder {!r}".format(folder))
            continue
        check_change(repo, rev, ARCHIVE_ROOT + folder + "/", match.group(4), report.errors, require_verification=True)
    report.notes.append("{} active and {} archived change(s) checked".format(len(active), len(archived)))
    if args.run_openspec and not report.errors:
        run_openspec(repo, rev, ["--all"], report.errors)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--mode", choices=("pr", "audit"), default="pr")
    parser.add_argument("--repo", default=".", help="repository root (default: current directory)")
    parser.add_argument("--base", help="trusted base revision (tip of the protected branch)")
    parser.add_argument("--head", default="HEAD", help="proposed revision (default: HEAD)")
    parser.add_argument("--rev", default="HEAD", help="revision to audit in --mode audit")
    parser.add_argument("--change", help="the approved OpenSpec change this implementation belongs to")
    parser.add_argument("--pr-body-env", help="environment variable holding the PR description")
    parser.add_argument("--base-ref-name", help="name of the PR's target branch, as reported by CI")
    parser.add_argument("--protected-branch", default="main")
    parser.add_argument("--trusted-ref", help="ref that must contain --base (e.g. origin/main)")
    parser.add_argument("--run-openspec", action="store_true", help="also run 'openspec validate --strict'")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.mode == "pr" and not args.base:
        print("governance: --base is required in pr mode", file=sys.stderr)
        return 2
    repo = Repo(os.path.abspath(args.repo))
    try:
        report = audit(args, repo) if args.mode == "audit" else check_pr(args, repo)
    except GitError as error:
        print("governance: FAIL (cannot determine revisions safely)\n  - {}".format(error), file=sys.stderr)
        return 2
    label = report.kind + (" ({})".format(report.change) if report.change else "")
    for note in report.notes:
        print("governance: " + note)
    if report.errors:
        print("governance: FAIL [{}]".format(label))
        for message in report.errors:
            print("  - " + message)
        return 1
    print("governance: PASS [{}]".format(label))
    return 0


if __name__ == "__main__":
    sys.exit(main())
