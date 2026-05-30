#!/usr/bin/env python3
"""Set the version field in all plugin manifests."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_FILES = [
    REPO_ROOT / "plugins/python-structured-logging/.codex-plugin/plugin.json",
    REPO_ROOT / "plugins/python-structured-logging/.claude-plugin/plugin.json",
]


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: set_plugin_version.py <x.y.z>", file=sys.stderr)
        return 1

    version = argv[1]
    if not SEMVER_RE.match(version):
        print("Version must match x.y.z (without 'v' prefix).", file=sys.stderr)
        return 1

    for path in PLUGIN_FILES:
        try:
            data = json.loads(path.read_text())
        except FileNotFoundError:
            print(f"Missing required file: {path}", file=sys.stderr)
            return 1
        except json.JSONDecodeError as exc:
            print(f"Invalid JSON in {path}: {exc}", file=sys.stderr)
            return 1

        data["version"] = version
        path.write_text(json.dumps(data, indent=2) + "\n")
        print(f"Updated {path} -> {version}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
