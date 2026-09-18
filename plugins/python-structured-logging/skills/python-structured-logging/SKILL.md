---
name: python-structured-logging
description: Review or improve Python logging with structlog, stdlib logging, or existing wrappers. Use for logging changes, not unrelated Python refactoring.
---

# Python Structured Logging

Make logs useful operational events while preserving the user's scope and the project's contracts.

## Scope and workflow

- For review requests, report findings with file locations and concrete effects; edit only when requested.
- Inspect the existing logger API, formatter/processors, exception ownership, and event conventions before proposing changes.
- Keep the current stack and wrappers. If migration would help, explain why; do not migrate without authorization.
- Preserve business behavior, function signatures, exception propagation, and retry decisions during logging refactors.
- Treat existing event names and fields as contracts that may feed alerts, dashboards, and queries. Preserve them unless changing that contract is in scope.
- When no convention exists, use stable `snake_case` events such as `invoice_processed`; put variable values in fields.
- Replace diagnostic `print` calls only when in scope. Preserve intentional CLI output.

## Choose the matching API

Read only the examples for the project's stack:

- **structlog:** [good](examples/structlog/good.py), [bad](examples/structlog/bad.py). Use keyword fields and a locally bound logger.
- **stdlib logging:** [good](examples/stdlib/good.py), [bad](examples/stdlib/bad.py). Use `extra` or the existing adapter; arbitrary keyword fields and `.bind()` are not stdlib APIs. `extra` adds LogRecord attributes, but the formatter must emit them. Avoid reserved LogRecord keys.
- **Project wrappers:** inspect their interface and output before adapting either pattern.

The example pairs have identical inputs and business behavior. Their operation owns the failure log; a caller must not log the same failure again.

## Fields and context

- Follow existing field names. For new fields, use explicit units such as `duration_ms` and `size_bytes`.
- Bind or inject shared context at a meaningful request/job boundary where supported. Repeating `extra` is acceptable when it is simpler and correct.
- A locally bound structlog logger does not automatically attach context to every logger in a request. For cross-module or concurrent context, read the [context lifecycle guidance](references/Python%20Logging%20Style%20Guide.md#context-lifecycle).
- Allowlist necessary payload fields before binding them. Do not log credentials, tokens, authorization headers, or raw sensitive payloads. Identifiers and payment-derived fields still need the project's data policy; masking alone does not make them universally safe.

## Exceptions and levels

- Identify the layer responsible for the final operational outcome. Log a failure once there; lower layers can propagate it without logging.
- Use `logger.exception(...)` inside `except` when a traceback is appropriate. Preserve the original control flow; do not introduce swallowing, re-raising, or retries merely to improve a log.
- Derive retryability from the real failure and retry policy, never from the presence of an exception.
- Tracebacks and exception messages can contain sensitive values even if structured fields are safe. Inspect the rendered output and use the existing sanitization path when needed.
- Use `INFO` for meaningful outcomes, `DEBUG` for optional diagnostics, `WARNING` for actionable degradation, and `ERROR` for failed operations needing attention, subject to project conventions.
- Avoid per-item loop noise and redundant boundary logs; retain start/progress events when they help diagnose long-running or stalled work.

## Verify the result

Check a representative success and failure through the configured output pipeline:

- Existing event/field contracts and application behavior are preserved.
- Fields survive formatting and serialization; no logger API errors occur.
- One appropriate failure record appears, with a traceback when needed.
- Sensitive values are absent from fields, messages, and rendered exceptions.
- Request/job context does not leak into another operation.

Use focused tests or output capture proportional to the change. Report what was checked and any unverified pipeline assumptions. Read the [reference guide](references/Python%20Logging%20Style%20Guide.md) for formatter, context, and exception edge cases.
