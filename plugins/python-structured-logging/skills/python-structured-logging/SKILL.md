---
name: python-structured-logging
description: Review or improve Python logging with structlog, stdlib logging, or existing wrappers. Use for logging changes, not unrelated Python refactoring.
---

# Python Structured Logging

Make logs useful operational events while preserving the user's scope and project contracts.

## Workflow

1. Determine whether the request is a review, a local logging change, or integration work. Review requests produce findings without edits.
2. Trace the affected logging path: its API, formatter/processors, event consumers, and failure owner as relevant. For a local change, stop when you can identify where the changed event renders and which contracts it touches; record unavailable configuration as an assumption.
3. Read the matching resources below, perform the requested work, and verify the applicable completion criteria.

## Scope and contracts

- Keep the stack and wrappers; migration requires authorization.
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

- Changing formatters/processors, configuring runtime logging, diagnosing missing fields, serialization, or duplicate handlers, or checking sensitive data across output paths: [output pipeline](references/output-pipeline.md).
- Working with cross-module or concurrent context or cleanup: [context lifecycle](references/context-lifecycle.md).
- Resolving failure ownership or sanitizing exception output: [exceptions and sensitive data](references/exceptions-and-sensitive-data.md).

## Context, exceptions, and noise

- Bind/inject shared context at request/job boundaries where supported; repeating `extra` is acceptable. A local `.bind()` does not enrich independent loggers. Clean up scoped context on success and failure without leaking between operations.
- Allowlist needed payload fields before binding. Never log credentials, tokens, authorization headers, or raw sensitive payloads. Identifiers and payment-derived fields still require the project's data policy; masking is not blanket permission.
- Log a failure once at the layer owning its operational outcome. Lower layers may propagate without logging. Use `logger.exception(...)` inside `except` when a traceback is appropriate; preserve control flow and derive retryability from the real policy.
- Exception messages and tracebacks can expose secrets despite safe fields. Inspect rendered output and use the existing sanitization path.
- Follow project levels: `INFO` for outcomes, `DEBUG` for optional diagnostics, `WARNING` for actionable degradation, `ERROR` for failed operations needing attention. Avoid per-item noise and redundant boundaries; retain useful progress for stalled or long-running work.

## Verify

Choose checks for the affected behavior; combine criteria when a task spans branches:

- **Review:** each finding has a location, concrete effect, and supporting evidence. Distinguish observed defects from unverified risks. Static review is sufficient when it establishes the finding; report runtime assumptions without requiring application startup.
- **Local change:** capture the changed event through the configured formatter, or a representative formatter when runtime configuration is unavailable. Confirm added fields survive and affected event contracts and application behavior remain intact. Keep checks scoped to the changed path.
- **Pipeline or sensitive-output change:** capture the complete configured runtime output boundary described in [output pipeline](references/output-pipeline.md), including failure and fallback paths. Verify configured output format and absence of sensitive values in fields, messages, and rendered exceptions.
- **Failure ownership change:** exercise the affected failure path; verify one appropriate failure record, traceback when needed, and unchanged propagation/retry behavior.
- **Context change:** exercise overlapping operations and cleanup on success and failure; check parent-context restoration for nested scopes.

Report checks performed, their observed results, and unverified pipeline assumptions. A representative formatter check does not establish full runtime safety.
