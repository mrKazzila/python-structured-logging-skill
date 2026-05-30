# Python Structured Logging Skill

Agent skill for adding, reviewing, refactoring, and standardizing structured logging in Python services. This repo follows the [Agent Skills specification](https://agentskills.io/specification), so it can be used by skills-compatible agents including Claude Code and Codex CLI.

The bundled skill is:

- `python-structured-logging`: Improve Python logging with a `structlog`-first approach, while also supporting the standard library `logging` module. Covers event naming, structured fields, bound context, exception logging, correlation IDs, noise reduction, and sensitive-data redaction.

## Installation

### Marketplace

```text
/plugin marketplace add mrKazzila/python-structured-logging-skill
/plugin install python-structured-logging@python-structured-logging-skill
```

### npx skills

```text
npx skills add git@github.com:mrKazzila/python-structured-logging-skill.git
```

Instead of SSH, if you prefer HTTPS:

```text
npx skills add https://github.com/mrKazzila/python-structured-logging-skill
```

### Manually

#### Claude Code

Copy the contents of this repo into a `/.claude` folder in the root of the project where you want the skill to be available.

See the [official Claude Skills documentation](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview).

#### Codex CLI

Copy the contents of [`plugins/python-structured-logging/skills/`](plugins/python-structured-logging/skills/) into your Codex skills path, typically `~/.codex/skills`.

See the [Agent Skills specification](https://agentskills.io/specification) for the standard skill format.

#### OpenCode

Clone the entire repo into the OpenCode skills directory:

```sh
git clone https://github.com/mrKazzila/python-structured-logging-skill.git ~/.opencode/skills/python-structured-logging-skill
```

Do not copy only the inner `skills/` folder. OpenCode auto-discovers `SKILL.md` files under `~/.opencode/skills/`.

## Skills

| Skill | Description |
|-------|-------------|
| [python-structured-logging](plugins/python-structured-logging/skills/python-structured-logging) | Add, review, refactor, and standardize structured logging in Python codebases, primarily with `structlog` and secondarily with the standard library `logging` module |

## Validation

To validate the skill folder structure and frontmatter, run:

```sh
uv run --with pyyaml python "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" plugins/python-structured-logging/skills/python-structured-logging
```

This uses the validator bundled with the local `skill-creator` skill installation.
