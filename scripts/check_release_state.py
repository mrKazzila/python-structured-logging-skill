#!/usr/bin/env python3
"""Validate release-relevant files for the skill repo."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
PLUGIN_FILES = [
    REPO_ROOT / "plugins/python-structured-logging/.codex-plugin/plugin.json",
    REPO_ROOT / "plugins/python-structured-logging/.claude-plugin/plugin.json",
]
SKILL_MD = REPO_ROOT / "plugins/python-structured-logging/skills/python-structured-logging/SKILL.md"


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        raise SystemExit(f"Missing required file: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}")


def validate_frontmatter() -> list[str]:
    errors: list[str] = []
    try:
        content = SKILL_MD.read_text()
    except FileNotFoundError:
        return [f"Missing required file: {SKILL_MD}"]

    if not content.startswith("---\n"):
        return [f"{SKILL_MD} is missing YAML frontmatter"]

    try:
        _, frontmatter, _ = content.split("---\n", 2)
    except ValueError:
        return [f"{SKILL_MD} has invalid frontmatter delimiters"]

    if not re.search(r"^name:\s+\S+", frontmatter, re.MULTILINE):
        errors.append(f"{SKILL_MD} frontmatter is missing 'name'")
    if not re.search(r"^description:\s+.+", frontmatter, re.MULTILINE):
        errors.append(f"{SKILL_MD} frontmatter is missing 'description'")
    return errors


def validate_versions(expected_version: str | None) -> list[str]:
    errors: list[str] = []
    versions: list[tuple[Path, str]] = []

    for path in PLUGIN_FILES:
        data = _read_json(path)
        version = data.get("version")
        if not isinstance(version, str):
            errors.append(f"{path} is missing string field 'version'")
            continue
        if not SEMVER_RE.match(version):
            errors.append(f"{path} has non-semver version: {version}")
            continue
        versions.append((path, version))

    unique_versions = {version for _, version in versions}
    if len(unique_versions) > 1:
        joined = ", ".join(f"{path.name}={version}" for path, version in versions)
        errors.append(f"Plugin versions are out of sync: {joined}")

    if expected_version is not None:
        if not SEMVER_RE.match(expected_version):
            errors.append(f"Expected version is not semver x.y.z: {expected_version}")
        elif unique_versions != {expected_version}:
            current = ", ".join(sorted(unique_versions)) or "<missing>"
            errors.append(
                f"Plugin versions do not match expected {expected_version}; current: {current}"
            )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-version")
    args = parser.parse_args()

    errors = []
    errors.extend(validate_frontmatter())
    errors.extend(validate_versions(args.expected_version))

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    version = _read_json(PLUGIN_FILES[0])["version"]
    print(f"Release state is valid for version {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
