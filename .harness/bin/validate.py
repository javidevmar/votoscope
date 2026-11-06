#!/usr/bin/env python3
"""Validate an SDD harness installation and optionally run project checks.

Usage:
    python3 validate.py [ROOT] [--run-checks] [--strict]

The validator is deliberately dependency-free (Python standard library only).
It checks the hard structural rules of the harness; judgement rules live in
CHECKPOINTS.md and the reviewer agent.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

DEFAULT_STATUSES = {"pending", "spec_ready", "in_progress", "done", "blocked"}
FEATURE_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
REQUIREMENT_RE = re.compile(r"^##\s+R(\d+)\b", re.MULTILINE)
TASK_RE = re.compile(r"^-\s+\[[ xX]\]\s+T(\d+)\b", re.MULTILINE)
UNCHECKED_TASK_RE = re.compile(r"^-\s+\[\s\]\s+T\d+\b", re.MULTILINE)
REQUIREMENT_REF_RE = re.compile(r"\bR(\d+)\b")
REQUIREMENT_RANGE_RE = re.compile(r"\bR(\d+)\s*[–-]\s*R(\d+)\b")


def referenced_requirements(text: str) -> set[int]:
    """Collect R<n> references, expanding ranges such as R1–R3."""
    referenced: set[int] = set()
    for start, end in REQUIREMENT_RANGE_RE.findall(text):
        first, last = int(start), int(end)
        if first <= last and last - first <= 100:
            referenced.update(range(first, last + 1))
    referenced.update(int(value) for value in REQUIREMENT_REF_RE.findall(text))
    return referenced

USE_COLOR = sys.stdout.isatty() and not os.environ.get("NO_COLOR")
GREEN = "\033[0;32m" if USE_COLOR else ""
YELLOW = "\033[0;33m" if USE_COLOR else ""
RED = "\033[0;31m" if USE_COLOR else ""
CYAN = "\033[0;36m" if USE_COLOR else ""
RESET = "\033[0m" if USE_COLOR else ""


class Report:
    def __init__(self) -> None:
        self.failures = 0
        self.warnings = 0

    def section(self, title: str) -> None:
        print(f"\n{CYAN}-- {title} {RESET}")

    def ok(self, message: str) -> None:
        print(f"{GREEN}[OK]{RESET}    {message}")

    def warn(self, message: str) -> None:
        self.warnings += 1
        print(f"{YELLOW}[WARN]{RESET}  {message}")

    def fail(self, message: str) -> None:
        self.failures += 1
        print(f"{RED}[FAIL]{RESET}  {message}")


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON: {exc}") from exc


def queue_enabled(config: dict[str, Any]) -> bool:
    """Targets use a feature queue by default; the harness source repo opts out."""
    return config.get("feature_queue", True) is not False


def normalize_commands(items: Any) -> list[dict[str, Any]]:
    """Accept strings or {name, command, required, timeout} objects."""
    if not isinstance(items, list):
        return []
    commands: list[dict[str, Any]] = []
    for item in items:
        if isinstance(item, str) and item.strip():
            commands.append(
                {"name": item, "command": item, "required": True, "timeout": None}
            )
            continue
        if not isinstance(item, dict):
            continue
        command = item.get("command")
        if not isinstance(command, str) or not command.strip():
            continue
        timeout = item.get("timeout")
        if not isinstance(timeout, int) or timeout <= 0:
            timeout = None
        commands.append(
            {
                "name": item.get("name") or command,
                "command": command,
                "required": item.get("required", True) is not False,
                "timeout": timeout,
            }
        )
    return commands


def run_commands(
    root: Path, commands: list[dict[str, Any]], label: str, report: Report
) -> None:
    if not commands:
        return
    for command in commands:
        report.section(f"{label}: {command['name']}")
        print(f"$ {command['command']}")
        try:
            result = subprocess.run(
                ["bash", "-c", command["command"]],
                cwd=root,
                timeout=command["timeout"],
            )
        except subprocess.TimeoutExpired:
            message = f"{label} '{command['name']}' timed out after {command['timeout']}s"
            if command["required"]:
                report.fail(message)
            else:
                report.warn(message)
            continue
        except OSError as exc:
            message = f"{label} '{command['name']}' could not run: {exc}"
            if command["required"]:
                report.fail(message)
            else:
                report.warn(message)
            continue

        if result.returncode == 0:
            report.ok(f"{label} '{command['name']}' passed")
        else:
            message = f"{label} '{command['name']}' failed (exit {result.returncode})"
            if command["required"]:
                report.fail(message)
            else:
                report.warn(message)


def check_required_files(root: Path, config: dict[str, Any], report: Report) -> None:
    paths = config.get("paths") if isinstance(config.get("paths"), dict) else {}
    agents = paths.get("agents", ".agents")
    progress = paths.get("progress", "progress")
    specs = paths.get("specs", "specs")
    feature_list = paths.get("feature_list", "feature_list.json")

    required = [
        "AGENTS.md",
        "CHECKPOINTS.md",
        "harness.config.json",
        "init.sh",
        "opencode.json",
        f"{agents}/specs.md",
        f"{agents}/architecture.md",
        f"{agents}/conventions.md",
        f"{agents}/style.md",
        f"{agents}/environment.md",
        f"{agents}/status.md",
        ".opencode/agents/leader.md",
        ".opencode/agents/spec-author.md",
        ".opencode/agents/test-generator.md",
        ".opencode/agents/implementer.md",
        ".opencode/agents/reviewer.md",
        ".opencode/agents/github-handler.md",
        ".opencode/commands/next-feature.md",
        ".opencode/commands/close-session.md",
        f"{specs}/_template/requirements.md",
        f"{specs}/_template/design.md",
        f"{specs}/_template/tasks.md",
    ]
    if queue_enabled(config):
        required.extend(
            [feature_list, f"{progress}/current.md", f"{progress}/history.md"]
        )

    missing = 0
    for relative in required:
        if (root / relative).is_file():
            continue
        missing += 1
        report.fail(f"missing required file: {relative}")
    if missing == 0:
        report.ok(f"required files present ({len(required)})")

    for relative in ("AGENTS.md", "CHECKPOINTS.md", f"{agents}/specs.md"):
        path = root / relative
        if path.is_file() and not path.read_text(encoding="utf-8").strip():
            report.fail(f"file is empty: {relative}")


def validate_config(
    config: dict[str, Any], report: Report, require_checks: bool
) -> None:
    if not isinstance(config.get("project"), str) or not config["project"].strip():
        report.fail("harness.config.json: 'project' must be a non-empty string")

    checks = config.get("checks")
    if not isinstance(checks, list):
        report.fail("harness.config.json: 'checks' must be an array")
    else:
        normalized = normalize_commands(checks)
        if not normalized:
            message = (
                "harness.config.json: no checks configured; "
                "add at least one real project check before running the gate"
            )
            if require_checks:
                report.fail(message)
            else:
                report.warn(message)
        else:
            report.ok(f"harness.config.json: {len(normalized)} check(s) configured")

    setup = config.get("setup")
    if setup is not None and not isinstance(setup, list):
        report.fail("harness.config.json: 'setup' must be an array")

    paths = config.get("paths")
    if paths is not None and not isinstance(paths, dict):
        report.fail("harness.config.json: 'paths' must be an object")

    agents = config.get("agents")
    if agents is not None and not isinstance(agents, dict):
        report.fail("harness.config.json: 'agents' must be an object")
    elif isinstance(agents, dict):
        max_in_progress = agents.get("max_features_in_progress", 1)
        if not isinstance(max_in_progress, int) or max_in_progress < 1:
            report.fail(
                "harness.config.json: agents.max_features_in_progress "
                "must be a positive integer"
            )

    sdd = config.get("sdd")
    if sdd is not None and not isinstance(sdd, dict):
        report.fail("harness.config.json: 'sdd' must be an object")
    elif isinstance(sdd, dict) and not isinstance(sdd.get("default", True), bool):
        report.fail("harness.config.json: sdd.default must be a boolean")

    feature_queue = config.get("feature_queue")
    if feature_queue is not None and not isinstance(feature_queue, bool):
        report.fail("harness.config.json: 'feature_queue' must be a boolean")


def validate_opencode(root: Path, report: Report) -> None:
    path = root / "opencode.json"
    if not path.is_file():
        return
    try:
        data = read_json(path)
    except ValueError as exc:
        report.fail(str(exc))
        return
    if not isinstance(data, dict):
        report.fail("opencode.json: expected a JSON object")
        return
    if data.get("default_agent") != "leader":
        report.warn("opencode.json: default_agent is not 'leader'")
    else:
        report.ok("opencode.json: default_agent is leader")


def validate_feature_list(
    root: Path, config: dict[str, Any], report: Report
) -> None:
    paths = config.get("paths") if isinstance(config.get("paths"), dict) else {}
    feature_list_path = root / paths.get("feature_list", "feature_list.json")
    specs_dir = root / paths.get("specs", "specs")
    progress_dir = root / paths.get("progress", "progress")

    try:
        data = read_json(feature_list_path)
    except FileNotFoundError:
        report.fail(f"missing feature list: {feature_list_path}")
        return
    except ValueError as exc:
        report.fail(str(exc))
        return

    if not isinstance(data, dict):
        report.fail("feature_list.json: expected a JSON object")
        return

    project = data.get("project")
    if not isinstance(project, str) or not project.strip():
        report.fail("feature_list.json: 'project' must be a non-empty string")
    elif project != config.get("project"):
        report.warn(
            "feature_list.json project "
            f"'{project}' does not match harness.config.json "
            f"'{config.get('project')}'"
        )

    rules = data.get("rules") if isinstance(data.get("rules"), dict) else {}
    raw_allowed = rules.get("valid_status")
    if (
        isinstance(raw_allowed, list)
        and raw_allowed
        and all(isinstance(item, str) for item in raw_allowed)
    ):
        allowed = set(raw_allowed)
    else:
        allowed = set(DEFAULT_STATUSES)

    agents = config.get("agents") if isinstance(config.get("agents"), dict) else {}
    max_in_progress = agents.get("max_features_in_progress", 1)
    if not isinstance(max_in_progress, int) or max_in_progress < 1:
        max_in_progress = 1

    sdd = config.get("sdd") if isinstance(config.get("sdd"), dict) else {}
    sdd_default = sdd.get("default", True)
    if not isinstance(sdd_default, bool):
        sdd_default = True

    features = data.get("features")
    if not isinstance(features, list):
        report.fail("feature_list.json: 'features' must be an array")
        return
    if not features:
        report.warn("feature_list.json: the queue is empty")
        return

    seen_ids: set[int] = set()
    seen_names: set[str] = set()
    in_progress = 0
    failures_before = report.failures

    for index, feature in enumerate(features, start=1):
        if not isinstance(feature, dict):
            report.fail(f"feature #{index}: expected an object")
            continue

        feature_id = feature.get("id")
        name = feature.get("name")
        status = feature.get("status")
        label = f"feature {feature_id!r} ({name!r})"

        if (
            not isinstance(feature_id, int)
            or isinstance(feature_id, bool)
            or feature_id < 1
        ):
            report.fail(f"{label}: id must be a positive integer")
            continue
        if feature_id in seen_ids:
            report.fail(f"{label}: duplicate id")
        seen_ids.add(feature_id)

        if not isinstance(name, str) or not FEATURE_NAME_RE.match(name):
            report.fail(
                f"{label}: name must match ^[a-z0-9][a-z0-9_-]*$"
            )
            name_ok = False
        elif name in seen_names:
            report.fail(f"{label}: duplicate name")
            name_ok = False
        else:
            seen_names.add(name)
            name_ok = True

        if not isinstance(feature.get("title"), str) or not feature["title"].strip():
            report.fail(f"{label}: title must be a non-empty string")

        if not isinstance(status, str) or status not in allowed:
            report.fail(f"{label}: invalid status {status!r}")
            continue

        if status == "in_progress":
            in_progress += 1

        sdd_flag = feature.get("sdd", sdd_default)
        if not isinstance(sdd_flag, bool):
            report.fail(f"{label}: 'sdd' must be a boolean")
            sdd_flag = sdd_default

        if status == "spec_ready" and not sdd_flag:
            report.fail(f"{label}: spec_ready requires sdd: true")

        acceptance = feature.get("acceptance")
        if status in {"pending", "in_progress", "done"} and not acceptance:
            report.warn(f"{label}: no acceptance criteria")

        if status == "blocked" and not feature.get("notes"):
            report.warn(f"{label}: blocked without a 'notes' reason")

        if not sdd_flag or status not in {"spec_ready", "in_progress", "done"}:
            continue
        if not name_ok:
            continue

        spec_dir = specs_dir / f"{feature_id:03d}_{name}"
        if not spec_dir.is_dir():
            report.fail(f"{label}: missing spec folder {spec_dir}")
            continue

        spec_files = {
            "requirements": spec_dir / "requirements.md",
            "design": spec_dir / "design.md",
            "tasks": spec_dir / "tasks.md",
        }
        missing = [key for key, path in spec_files.items() if not path.is_file()]
        for key in missing:
            report.fail(f"{label}: missing {spec_files[key]}")
        if missing:
            continue

        requirements_text = spec_files["requirements"].read_text(encoding="utf-8")
        design_text = spec_files["design"].read_text(encoding="utf-8")
        tasks_text = spec_files["tasks"].read_text(encoding="utf-8")

        requirement_ids = [int(value) for value in REQUIREMENT_RE.findall(requirements_text)]
        if not requirement_ids:
            report.fail(f"{label}: requirements.md has no '## R<n>' sections")
        if "MUST" not in requirements_text:
            report.warn(f"{label}: requirements.md has no MUST clause")
        if not design_text.strip():
            report.fail(f"{label}: design.md is empty")

        task_ids = [int(value) for value in TASK_RE.findall(tasks_text)]
        if not task_ids:
            report.fail(f"{label}: tasks.md has no '- [ ] T<n>' tasks")

        if status == "done":
            unchecked = UNCHECKED_TASK_RE.findall(tasks_text)
            if unchecked:
                report.fail(
                    f"{label}: done feature still has {len(unchecked)} unchecked task(s)"
                )
            for artifact in (
                progress_dir / f"impl_{name}.md",
                progress_dir / f"review_{name}.md",
            ):
                if not artifact.is_file():
                    report.fail(f"{label}: missing {artifact.name}")
            review_path = progress_dir / f"review_{name}.md"
            if review_path.is_file():
                verdict = re.search(
                    r"(?:verdict|veredicto)\s*:?\s*\**\s*"
                    r"(APPROVED|CHANGES_REQUESTED)",
                    review_path.read_text(encoding="utf-8"),
                    re.IGNORECASE,
                )
                if verdict is None:
                    report.fail(
                        f"{label}: {review_path.name} has no "
                        "'Verdict: APPROVED | CHANGES_REQUESTED' line"
                    )
                elif verdict.group(1).upper() != "APPROVED":
                    report.fail(f"{label}: review verdict is not APPROVED")

        mentioned = referenced_requirements(tasks_text)
        for requirement_id in requirement_ids:
            if requirement_id not in mentioned:
                report.warn(
                    f"{label}: requirement R{requirement_id} is not referenced "
                    "by any task"
                )

    if in_progress > max_in_progress:
        report.fail(
            f"{in_progress} features are in_progress (max {max_in_progress})"
        )
    elif report.failures == failures_before:
        report.ok(f"{len(features)} feature(s); {in_progress} in progress")


def validate_progress(root: Path, config: dict[str, Any], report: Report) -> None:
    paths = config.get("paths") if isinstance(config.get("paths"), dict) else {}
    progress_dir = root / paths.get("progress", "progress")
    for name in ("current.md", "history.md"):
        path = progress_dir / name
        if path.is_file() and not path.read_text(encoding="utf-8").strip():
            report.fail(f"{progress_dir.name}/{name} is empty")
    current = progress_dir / "current.md"
    if current.is_file():
        text = current.read_text(encoding="utf-8")
        if "Feature in progress" not in text:
            report.warn("progress/current.md has no 'Feature in progress' line")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate an SDD harness installation and optionally run checks."
    )
    parser.add_argument("root", nargs="?", default=".", help="target repository")
    parser.add_argument(
        "--run-checks",
        action="store_true",
        help="run setup commands and checks from harness.config.json",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="treat warnings as failures",
    )
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    report = Report()
    print(f"{CYAN}SDD harness gate{RESET}  {root}")

    config_path = root / "harness.config.json"
    if not config_path.is_file():
        report.fail(f"missing harness.config.json in {root}")
        print(f"\n{RED}Harness not ready.{RESET}")
        return 1

    try:
        config = read_json(config_path)
    except ValueError as exc:
        report.fail(str(exc))
        print(f"\n{RED}Harness not ready.{RESET}")
        return 1

    if not isinstance(config, dict):
        report.fail("harness.config.json: expected a JSON object")
        print(f"\n{RED}Harness not ready.{RESET}")
        return 1

    setup = normalize_commands(config.get("setup"))
    checks = normalize_commands(config.get("checks"))

    if args.run_checks:
        run_commands(root, setup, "setup", report)

    report.section("Files")
    check_required_files(root, config, report)

    report.section("Config")
    validate_config(config, report, require_checks=args.run_checks)

    report.section("OpenCode")
    validate_opencode(root, report)

    report.section("Feature queue")
    if queue_enabled(config):
        validate_feature_list(root, config, report)

        report.section("Bitácora")
        validate_progress(root, config, report)
    else:
        report.ok("disabled (feature_queue: false)")

    if args.run_checks:
        report.section("Checks")
        if checks:
            run_commands(root, checks, "check", report)

    if args.strict and report.warnings:
        report.fail(f"strict mode: {report.warnings} warning(s)")

    print(f"\n{CYAN}Summary{RESET}")
    if report.failures == 0:
        print(f"{GREEN}[OK]{RESET}    harness ready ({report.warnings} warning(s))")
        return 0
    print(
        f"{RED}[FAIL]{RESET}  harness not ready "
        f"({report.failures} failure(s), {report.warnings} warning(s))"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
