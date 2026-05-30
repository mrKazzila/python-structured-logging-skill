[group('Quality')]
[doc('To validate the skill folder structure and frontmatter')]
validate:
    @uv run --with pyyaml python "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" plugins/python-structured-logging/skills/python-structured-logging
