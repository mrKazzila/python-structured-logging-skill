---
name: python-structured-logging
description: Review or improve Python logging with structlog, stdlib logging, or existing wrappers. Use for logging changes, not unrelated Python refactoring.
---

# Python Structured Logging

Make logs useful operational events while preserving the user's scope and project contracts.

## Scope and contracts

- Review requests need findings with locations and concrete effects, not edits.
- Inspect the logger API, formatter/processors, event conventions, and failure ownership. Keep the stack and wrappers; migration requires authorization.
- Preserve business behavior, signatures, exception propagation, and retry decisions.
- Event names and fields may feed alerts, dashboards, and queries. Preserve existing contracts, including dotted names. Before an authorized rename, inspect available consumers and explain their updates; report external consumers you cannot verify.
- With no existing convention, use stable `snake_case` events such as `invoice_processed` and put variable values in fields. Follow existing field names; give new units explicit keys such as `duration_ms`.
- Replace diagnostic prints only in scope; preserve intentional CLI output.

## API and selective reading

Read the matching example pair for substantial refactoring, integration setup, or API uncertainty. Simple field additions and local reviews do not require examples.

- **structlog:** keyword fields and a locally bound logger; [good](examples/structlog/good.py), [bad](examples/structlog/bad.py).
- **stdlib:** `extra` or existing adapters; no arbitrary keyword fields or `.bind()`. Avoid reserved LogRecord keys. The formatter must emit added attributes; [good](examples/stdlib/good.py), [bad](examples/stdlib/bad.py).
- **Wrappers:** inspect their interface and output before adapting either pattern.

Read only the relevant reference when:

- Changing formatters/processors, diagnosing missing fields, serialization, or duplicate handlers: [output pipeline](references/output-pipeline.md).
- Working with cross-module or concurrent context or cleanup: [context lifecycle](references/context-lifecycle.md).
- Resolving failure ownership or sanitizing exception output: [exceptions and sensitive data](references/exceptions-and-sensitive-data.md).

## Context, exceptions, and noise

- Bind/inject shared context at request/job boundaries where supported; repeating `extra` is acceptable. A local `.bind()` does not enrich independent loggers. Clean up scoped context on success and failure without leaking between operations.
- Allowlist needed payload fields before binding. Never log credentials, tokens, authorization headers, or raw sensitive payloads. Identifiers and payment-derived fields still require the project's data policy; masking is not blanket permission.
- Log a failure once at the layer owning its operational outcome. Lower layers may propagate without logging. Use `logger.exception(...)` inside `except` when a traceback is appropriate; preserve control flow and derive retryability from the real policy.
- Exception messages and tracebacks can expose secrets despite safe fields. Inspect rendered output and use the existing sanitization path.
- Follow project levels: `INFO` for outcomes, `DEBUG` for optional diagnostics, `WARNING` for actionable degradation, `ERROR` for failed operations needing attention. Avoid per-item noise and redundant boundaries; retain useful progress for stalled or long-running work.

## Verify

Use focused tests/output capture proportional to the change, through the complete configured runtime output boundary (see [output pipeline](references/output-pipeline.md)):

- Contracts and application behavior preserved; fields survive formatting without API errors.
- One appropriate failure record, with traceback when needed; no sensitive values in fields, messages, or rendered exceptions.
- Request/job context isolated and cleaned up.

Report checks performed and unverified pipeline assumptions.
