---
name: python-structured-logging
description: Add, review, refactor, and standardize structured logging in Python codebases, primarily with structlog and secondarily with the standard library logging module. Use when Codex needs to improve logs in FastAPI apps, async workers, CLI tools, background jobs, Kafka or Redis consumers, Celery or taskiq tasks, or service-layer code, including event naming, canonical fields, bound context, exception logging, correlation IDs, noise reduction, and sensitive-data redaction.
---

# Python Structured Logging

Improve logs so they are useful to operators, safe to ship, and easy to query.

## Use this workflow

1. Identify the logging stack already in use: `structlog`, stdlib `logging`, `loguru`, or a project wrapper.
2. Preserve existing conventions unless they are clearly harmful or the user asks to standardize them.
3. If `structlog` is available or already used, prefer it as the primary implementation style.
4. Prefer stable event names plus structured fields over interpolated text messages.
5. Bind shared request or task context once instead of repeating it in every call.
6. Keep one meaningful log per event boundary; remove noisy start or end chatter.
7. Preserve traceback data for unexpected failures and avoid duplicate exception logs across layers.
8. Remove or redact secrets, tokens, cookies, full payloads, and unnecessary personal data.
9. Verify changes with targeted tests or focused code inspection where possible.

## Enforce these defaults

- Write event names in `snake_case`.
- Keep event names short, stable, and free of variable values.
- Put variable data into fields such as `user_id`, `request_id`, `duration_ms`, `status`, or `reason`.
- Choose levels by operational meaning: `DEBUG` for diagnostics, `INFO` for expected events, `WARNING` for degradations or retries, `ERROR` for failed operations, `CRITICAL` only for service-threatening states.
- Use unit-bearing names such as `duration_ms`, `delay_seconds`, `size_bytes`, and `timeout_seconds`.
- Log success only when it is operationally meaningful.
- Add context at the layer where an operator can act on it; do not log and re-raise at every layer.

## Review checklist

Check each touched log statement for:

- stable event naming;
- structured fields instead of f-strings or `%s`-style narrative text;
- useful identifiers and outcome fields;
- correct log level;
- traceback preservation on unexpected exceptions;
- absence of duplicated logs for the same failure path;
- absence of sensitive data leakage;
- signal-to-noise quality.

## Framework guidance

- For `structlog`, prefer `bind()` or `structlog.contextvars` for request or task scope. Keep events stable and pass variable data as keyword fields.
- For stdlib `logging`, prefer `extra=` or the project adapter rather than interpolating variables into the message.
- For wrappers or mixed stacks, fit the existing emission API and improve the event shape without forcing a full logging rewrite unless requested.

## Use bundled resources

- Read [references/Python Logging Style Guide.md](references/Python%20Logging%20Style%20Guide.md) when you need the full doctrine, naming guidance, field conventions, or rationale.
- Read [examples/structlog/good.py](examples/structlog/good.py) and [examples/structlog/bad.py](examples/structlog/bad.py) for the preferred structlog style.
- Read [examples/stdlib/good.py](examples/stdlib/good.py) and [examples/stdlib/bad.py](examples/stdlib/bad.py) when the project is intentionally using standard library logging without structlog.

## Output expectations

When changing code:

- keep edits local to the touched flow;
- prefer a small number of canonical events over verbose traces;
- note any field naming standard you introduce;
- mention residual risks such as missing request context plumbing, absent JSON rendering, or unresolved sensitive-data exposure.
