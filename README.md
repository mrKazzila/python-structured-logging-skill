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

Copy the inner `plugins/python-structured-logging/skills/python-structured-logging` directory, including its examples and references. Run these commands from the repository root; choose the location for your client.

| Client / scope | Destination |
| --- | --- |
| Claude Code / project | `<project>/.claude/skills/python-structured-logging` |
| Codex / user | `~/.agents/skills/python-structured-logging` |
| OpenCode / user | `~/.config/opencode/skills/python-structured-logging` |

For example, for Codex:

```sh
mkdir -p ~/.agents/skills
cp -R plugins/python-structured-logging/skills/python-structured-logging ~/.agents/skills/
```

For an existing installation, update its contents rather than nesting another copy. Do not copy the entire repository into a skill directory.

Verify discovery in a fresh client session: use `/python-structured-logging` for a manually installed Claude Code skill, `/skills` or `$python-structured-logging` in Codex, or ask OpenCode to list available skills. For Claude plugin installation, the command is namespaced as `/python-structured-logging:python-structured-logging`.

See the official [Claude Code](https://code.claude.com/docs/en/skills), [Codex](https://learn.chatgpt.com/docs/build-skills), and [OpenCode](https://opencode.ai/docs/skills/) documentation. Paths were checked against documentation on 2026-09-18; discovery still needs a smoke test in your client version.

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

- The task is unrelated to logging. Review-only requests are supported and must not change files.
- The task is a one-off throwaway script where logging would add more noise than value.
- The project has strict logging conventions and the current task is unrelated to logging or observability.

## Verify / Contribute

Requires Python 3.12+ and either `uv` with `just`, or a Python virtual environment. No local Codex installation is needed.

```sh
just check
```

Equivalent commands without `just` or `uv`:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python scripts/validate_repo.py
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/check_release_state.py
```

Dependencies are pinned in `requirements-dev.txt`. The first installation requires access to a package index. `just validate` runs structural validation; `just test` runs executable example and validator regression checks. CI runs these checks on pull requests, branch pushes, and before a release.

Behavioral agent evaluation is separate: see [evals/README.md](evals/README.md) for fixtures, prompts, acceptance criteria, and skill/no-skill comparisons. Passing structural checks does not establish agent quality.

Keep changes scoped and update examples or eval cases when the recommended behavior changes.

## License

This project is licensed under the terms in [LICENSE](LICENSE).
