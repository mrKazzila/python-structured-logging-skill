# Python Logging Style Guide

Use this reference when you need human-oriented guidance for reviewing or improving logs in Python code. The skill file is the execution checklist; this guide adds rationale, examples, and migration patterns. Prefer `structlog` when the project already uses it, and keep stdlib `logging` when the project intentionally standardized on it.

## Core Rules

- Treat each log as an operational event.
- Keep event names short, stable, and in `snake_case`.
- Put variable data into fields, not interpolated prose.
- Bind shared context once when possible.
- Preserve stack traces for unexpected failures.
- Redact sensitive data before it reaches logs.
- Keep debug noise on a short leash.

## Event Naming

Prefer event names like:

```python
"invoice_processed"
"retry_scheduled"
"broker_publish_failed"
```

Avoid event names like:

```python
"Invoice processed successfully!"
f"invoice_{invoice_id}_processed"
"something went wrong"
```

Good:

```python
logger.info("invoice_processed", invoice_id=invoice_id, duration_ms=duration_ms)
```

Bad:

```python
logger.info(f"invoice {invoice_id} processed in {duration_ms} ms")
```

## Field Naming Conventions

Use stable `snake_case` field names and explicit units.

Preferred fields:

```text
request_id
correlation_id
job_id
user_id
entity_id
status
reason
error_code
duration_ms
delay_seconds
size_bytes
attempt
max_attempts
```

Guidelines:

- One concept should keep one name across the project.
- IDs should normally end with `_id`.
- Units belong in the key name, not only in the value.
- Avoid repeating the same shared fields on every log if the stack supports binding or adapters.

When logging payload-derived data, prefer allowlisted fragments over whole payloads. For example, log `card_last4`, `amount_cents`, or `item_count`, not the raw request body.

## Level Guide

- `DEBUG`: local diagnostics and temporary deep inspection.
- `INFO`: expected business or operational events.
- `WARNING`: degraded but handled situations such as retries or fallbacks.
- `ERROR`: a concrete operation failed and needs attention.
- `CRITICAL`: service-threatening state or probable data-loss scenario.

Do not log every function entry and exit at `INFO`. Use `DEBUG` sparingly, and only when the details are actionable.

## Exception Logging

Use `logger.exception(...)` inside `except` when you need traceback data.

Good:

```python
try:
    publish(message)
except ProviderTimeoutError:
    logger.exception("publish_failed", message_id=message_id, retryable=True)
    raise
```

Bad:

```python
try:
    publish(message)
except Exception as exc:
    logger.error(f"publish failed: {exc}")
```

Rules:

- Do not log and swallow unless that is the intended control flow.
- Do not duplicate the same exception log at every layer.
- Add enough context for operators to know what failed and whether it will retry.
- Avoid `logger.error(str(exc))` as the only record for an unexpected failure.

## Sensitive Data

Never log:

- passwords
- tokens
- API keys
- cookies
- authorization headers
- private keys
- raw secrets
- raw request bodies
- raw response bodies
- session data
- personal data
- payment data
- raw payloads containing PII or credentials

Prefer allowlisted payload logging.

Good:

```python
logger.info(
    "payment_authorized",
    payment={"amount_cents": amount_cents, "card_last4": card_last4},
)
```

Bad:

```python
logger.info("payment_authorized", payload=payment_payload, auth_header=auth_header)
```

## structlog and stdlib Patterns

`structlog`:

```python
log = logger.bind(request_id=request_id, job_id=job_id)
log.info("job_started", task_name=task_name)
```

Stdlib `logging`:

```python
logger.info(
    "job_started",
    extra={"request_id": request_id, "job_id": job_id, "task_name": task_name},
)
```

In both styles, keep the event name stable and treat the surrounding fields as the query surface. If a downstream formatter or adapter already shapes the record, follow that path instead of inventing a parallel one.

## Migration Notes

From `print` debugging:

```python
print("processing invoice", invoice_id)
```

To structured logging:

```python
logger.debug("invoice_processing", invoice_id=invoice_id)
```

From prose logging:

```python
logger.info(f"user {user_id} updated account status to {status}")
```

To structured events:

```python
logger.info("account_status_updated", user_id=user_id, status=status)
```

From repeated manual context:

```python
logger.info("step_one", request_id=request_id, user_id=user_id)
logger.info("step_two", request_id=request_id, user_id=user_id)
```

To bound context:

```python
log = logger.bind(request_id=request_id, user_id=user_id)
log.info("step_one")
log.info("step_two")
```
