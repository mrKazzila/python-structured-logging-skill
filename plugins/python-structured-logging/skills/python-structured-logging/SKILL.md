---
name: python-structured-logging
description: Use when reviewing or changing Python logging behavior, including structlog, stdlib logging, event naming, structured fields, bound context, exception logging, correlation IDs, or sensitive-data-safe observability.
---

# Python Structured Logging

## Core Rule

Logs are operational events, not developer diary entries.

## Workflow

1. Inspect the current stack first: `structlog`, stdlib `logging`, or a project wrapper.
2. Preserve the current direction unless it is harmful or migration was explicitly requested.
3. If the project uses stdlib `logging` intentionally, improve message shape and `extra` fields instead of forcing `structlog`.
4. Replace prose or dynamic event names with stable `snake_case` events.
5. Move variable data into structured fields and bind shared context once near the request or job boundary.
6. Keep one meaningful exception log at the layer that owns the failure, with a traceback when needed.
7. Remove or redact sensitive data before it reaches bound context or payload fields.
8. Verify output shape, levels, and noise after the change.

## Event Naming

- Use stable `snake_case` event names.
- Prefer action or action-plus-result names such as `invoice_processed` or `broker_publish_failed`.
- Do not put IDs, emails, statuses, or exception text into the event name.
- Do not use generic events such as `error`, `failed`, or `something_went_wrong` without the operation name.

Good:

```python
logger.info("invoice_processed", invoice_id=invoice_id, duration_ms=duration_ms)
logger.warning("retry_scheduled", attempt=attempt, delay_seconds=delay_seconds)
```

Bad:

```python
logger.info(f"invoice {invoice_id} processed in {duration_ms} ms")
logger.error(f"publish failed for order {order_id}")
logger.info(f"user_{user_id}_updated")
```

## Fields and Context

- Use stable field names such as `request_id`, `correlation_id`, `job_id`, `user_id`, `entity_id`, `status`, and `duration_ms` when they are relevant.
- Bind shared context once when possible instead of passing the same fields manually everywhere.
- Keep units in the key name: `duration_ms`, `delay_seconds`, `size_bytes`.
- Avoid renaming the same concept across modules.
- Prefer allowlisted payload fragments such as `{"amount_cents": ..., "card_last4": ...}` over raw payload logging.

Good:

```python
log = logger.bind(request_id=request_id, job_id=job_id)
log.info("job_started", task_name=task_name)
```

Bad:

```python
logger.info("job started", extra={"req": request_id, "job": job_id})
logger.info("job_started", request_id=request_id, job_id=job_id)
logger.info("job_finished", request_id=request_id, job_id=job_id)
```

## Exception Logging

- Use `logger.exception(...)` inside `except` when you need the traceback.
- Use `exc_info=True` only when the logger API requires it.
- Do not log and swallow unless that behavior is intentional and the caller does not need the failure.
- Do not duplicate the same exception log at every layer.
- Do not use `logger.error(str(exc))` as the only exception log for unexpected failures.

Good:

```python
try:
    send_invoice(invoice)
except ProviderTimeoutError:
    logger.exception("invoice_send_failed", invoice_id=invoice.id, retryable=True)
    raise
```

Bad:

```python
try:
    send_invoice(invoice)
except Exception as exc:
    logger.error(f"invoice failed: {exc}")
```

## Sensitive Data

- Never log passwords, tokens, API keys, cookies, authorization headers, private keys, or raw secrets.
- Never log raw request bodies, raw response bodies, session data, personal data, or payment data unless the user explicitly asks for a safe, scoped format.
- Prefer allowlisted fields over blocklists when logging payload-derived data.
- Redact at boundaries before binding context.

Good:

```python
safe_payment = {
    "card_last4": payment.card_last4,
    "amount_cents": payment.amount_cents,
}
logger.info("payment_authorized", payment=safe_payment)
```

Bad:

```python
logger.info("payment_authorized", payload=payment_payload, auth_header=auth_header)
```

## Noise Control

- `INFO` for business or operational events that matter.
- `DEBUG` for local diagnostics that can be turned off safely.
- `WARNING` for degraded but handled situations such as retries or fallbacks.
- `ERROR` for failed operations that need attention.
- Avoid logs inside tight loops unless they are sampled or aggregated.
- Remove `started` and `finished` chatter unless the boundary is operationally meaningful.
- Prefer one outcome log over multiple step-by-step logs when the extra detail does not change operator action.

## Bundled Resources

- [`examples/structlog/good.py`](examples/structlog/good.py)
- [`examples/structlog/bad.py`](examples/structlog/bad.py)
- [`examples/stdlib/good.py`](examples/stdlib/good.py)
- [`examples/stdlib/bad.py`](examples/stdlib/bad.py)
- [`references/Python Logging Style Guide.md`](references/Python Logging Style Guide.md)

- Read the examples that match the stack already in use.
- Read the reference guide when you need human-oriented rationale, level guidance, or migration examples.

## Verification Checklist

- Current logging style is preserved or intentionally migrated.
- Event names are stable and `snake_case`.
- Variable data is in fields, not prose strings.
- Shared context is bound or injected once where the stack supports it.
- Exceptions include stack traces where needed.
- Sensitive data is redacted or omitted.
- Output still fits the project's log pipeline.
