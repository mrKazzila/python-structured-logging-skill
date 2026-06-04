# Python Structured Logging Skill

`python-structured-logging` is a skill for coding agents working in Python codebases that need clearer, safer, and more queryable logs. It helps with practical tasks such as reviewing noisy log statements, replacing `print` debugging, standardizing event names and fields, and improving exception logging.

The canonical skill id is `python-structured-logging`. This repository is named `python-structured-logging-skill` and packages that skill for skills-compatible agent environments.

## Quickstart

### Marketplace

```text
/plugin marketplace add mrKazzila/python-structured-logging-skill
/plugin install python-structured-logging@python-structured-logging-skill
```

Use the marketplace path only if your agent runtime supports these plugin commands.

### npx skills

```text
npx skills add git@github.com:mrKazzila/python-structured-logging-skill.git
```

If you prefer HTTPS:

```text
npx skills add https://github.com/mrKazzila/python-structured-logging-skill
```

### Manual install

#### Claude Code

Copy this repository into the target project's `/.claude` folder.

See the [official Claude Skills documentation](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview).

#### Codex CLI

Copy [`plugins/python-structured-logging/skills/python-structured-logging`](plugins/python-structured-logging/skills/python-structured-logging) into your Codex skills path, typically `~/.codex/skills/python-structured-logging`.

See the [Agent Skills specification](https://agentskills.io/specification) for the standard skill format.

#### OpenCode

Clone the entire repo into the OpenCode skills directory:

```sh
git clone https://github.com/mrKazzila/python-structured-logging-skill.git ~/.opencode/skills/python-structured-logging-skill
```

Do not copy only the inner `skills/` folder. OpenCode auto-discovers `SKILL.md` files under `~/.opencode/skills/`.

The skill inspects the logging stack already in use before changing anything. If the project already uses `structlog`, it leans into bound context and structured fields. If the project intentionally uses stdlib `logging`, it improves event names, `extra` payloads, and traceback handling without forcing a migration.

## What's Inside

- Main skill: [`plugins/python-structured-logging/skills/python-structured-logging/SKILL.md`](plugins/python-structured-logging/skills/python-structured-logging/SKILL.md)
- Examples: [`examples/structlog`](plugins/python-structured-logging/skills/python-structured-logging/examples/structlog) and [`examples/stdlib`](plugins/python-structured-logging/skills/python-structured-logging/examples/stdlib)
- Reference guide: [`references/Python Logging Style Guide.md`](plugins/python-structured-logging/skills/python-structured-logging/references/Python Logging Style Guide.md)
- Agent metadata: [`agents/openai.yaml`](plugins/python-structured-logging/skills/python-structured-logging/agents/openai.yaml)

## When to Use This Skill

- Adding or upgrading logging in a Python service, worker, CLI, or background job.
- Reviewing whether existing logs are structured, stable, and operationally useful.
- Replacing `print` statements and ad hoc debug logging.
- Introducing structured fields into existing `structlog` or stdlib `logging` code.
- Standardizing event names and field names across modules or teams.
- Debugging production behavior that needs better context and lower noise.

## When Not to Use

- The user explicitly asked not to change logging behavior.
- The task is a one-off throwaway script where logging would add more noise than value.
- The project has strict logging conventions and the current task is unrelated to logging or observability.

## Verify / Contribute

- Edit the skill or reference guide.
- Update examples if the recommended behavior changes.
- Run checks before finishing:

```sh
just validate
python scripts/check_release_state.py
```

- `just validate` uses `uv` plus `pyyaml`. If `pyyaml` is not already available, `uv` may need a writable cache and network access to fetch it.
- `uv run python scripts/check_release_state.py` is an equivalent release-state check if you prefer to keep the command under `uv`.
- Keep the skill concise, direct, and usable by agents during review and refactoring.

## License

This project is licensed under the terms in [LICENSE](LICENSE).
