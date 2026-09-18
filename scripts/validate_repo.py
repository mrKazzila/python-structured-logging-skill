#!/usr/bin/env python3
"""Validate this repository's skill and distribution metadata."""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

import yaml

ROOT = Path(__file__).resolve().parent.parent
SKILL_NAME = "python-structured-logging"
PLUGIN = Path("plugins") / SKILL_NAME
SKILL = PLUGIN / "skills" / SKILL_NAME


def validate(root: Path = ROOT) -> list[str]:
    errors: list[str] = []

    def mapping(path: Path, loader) -> dict:
        try:
            value = loader(path.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise ValueError("expected a mapping")
            return value
        except (OSError, ValueError, yaml.YAMLError) as exc:
            errors.append(f"{path.relative_to(root)}: {exc}")
            return {}

    skill_path = root / SKILL
    entrypoint = skill_path / "SKILL.md"
    try:
        text = entrypoint.read_text(encoding="utf-8")
    except OSError as exc:
        return [str(exc)]
    match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", text, re.DOTALL)
    metadata = {}
    if not match:
        errors.append("SKILL.md: missing YAML frontmatter delimiters")
    else:
        try:
            metadata = yaml.safe_load(match.group(1))
            if not isinstance(metadata, dict):
                raise ValueError("frontmatter must be a mapping")
        except (ValueError, yaml.YAMLError) as exc:
            errors.append(f"SKILL.md: {exc}")
            metadata = {}
    name = metadata.get("name")
    if name != skill_path.name:
        errors.append("SKILL.md: name must match the skill directory")
    if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) or len(name) > 64:
        errors.append("SKILL.md: invalid skill name")
    description = metadata.get("description")
    if not isinstance(description, str) or not description.strip() or len(description) > 1024:
        errors.append("SKILL.md: description must be a nonempty string of at most 1024 characters")

    # Repository docs use inline Markdown links. Resolve local paths, not web links.
    documents = [root / "README.md", *skill_path.rglob("*.md"), *(root / "evals").rglob("*.md")]
    for document in documents:
        if not document.is_file():
            errors.append(f"Missing document: {document.relative_to(root)}")
            continue
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", document.read_text()):
            target = target.strip("<>")
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            destination = (document.parent / unquote(parsed.path)).resolve()
            if not destination.is_relative_to(root.resolve()) or not destination.exists():
                errors.append(f"{document.relative_to(root)}: missing or external local resource {target}")

    ui = mapping(skill_path / "agents/openai.yaml", yaml.safe_load)
    interface = ui.get("interface")
    if not isinstance(interface, dict):
        errors.append("agents/openai.yaml: missing interface mapping")
    else:
        for key in ("display_name", "short_description", "default_prompt"):
            if not isinstance(interface.get(key), str) or not interface[key].strip():
                errors.append(f"agents/openai.yaml: missing {key}")
        prompt = interface.get("default_prompt")
        if not isinstance(prompt, str) or f"${SKILL_NAME}" not in prompt:
            errors.append("agents/openai.yaml: default_prompt must invoke the skill")

    for directory in (".codex-plugin", ".claude-plugin"):
        data = mapping(root / PLUGIN / directory / "plugin.json", json.loads)
        if data.get("name") != SKILL_NAME:
            errors.append(f"{directory}/plugin.json: inconsistent plugin name")

    for directory in (".agents/plugins", ".claude-plugin"):
        data = mapping(root / directory / "marketplace.json", json.loads)
        plugins = data.get("plugins")
        if not isinstance(plugins, list) or len(plugins) != 1 or not isinstance(plugins[0], dict):
            errors.append(f"{directory}: expected one plugin entry")
            continue
        plugin = plugins[0]
        if plugin.get("name") != SKILL_NAME or plugin.get("source") != f"./{PLUGIN.as_posix()}":
            errors.append(f"{directory}: plugin name/source does not match the bundled plugin")
        if not (root / PLUGIN).is_dir():
            errors.append(f"{directory}: plugin source directory is missing")

    cases = mapping(root / "evals/cases.json", json.loads).get("cases")
    if not isinstance(cases, list) or not cases:
        errors.append("evals/cases.json: expected nonempty cases list")
    else:
        seen = set()
        for case in cases:
            if not isinstance(case, dict):
                errors.append("evals/cases.json: each case must be a mapping")
                continue
            case_id = case.get("id")
            if not isinstance(case_id, str) or not case_id or case_id in seen:
                errors.append("evals/cases.json: missing or duplicate case id")
            else:
                seen.add(case_id)
            for key in ("prompt",):
                if not isinstance(case.get(key), str) or not case[key].strip():
                    errors.append(f"eval {case_id}: missing {key}")
            if not isinstance(case.get("should_trigger"), bool):
                errors.append(f"eval {case_id}: should_trigger must be boolean")
            criteria = case.get("criteria")
            if not isinstance(criteria, list) or not criteria or not all(isinstance(c, str) and c.strip() for c in criteria):
                errors.append(f"eval {case_id}: missing acceptance criteria")
            fixtures = case.get("fixtures")
            if not isinstance(fixtures, list) or not fixtures:
                errors.append(f"eval {case_id}: missing fixtures")
                continue
            for fixture in fixtures:
                if not isinstance(fixture, str):
                    errors.append(f"eval {case_id}: invalid fixture path")
                    continue
                path = (root / fixture).resolve()
                if not path.is_relative_to(root.resolve()) or not path.is_file():
                    errors.append(f"eval {case_id}: missing fixture {fixture}")
    return errors


if __name__ == "__main__":
    problems = validate()
    for problem in problems:
        print(problem)
    if problems:
        raise SystemExit(1)
    print("Skill, resource links, plugin paths, and eval cases are valid")
