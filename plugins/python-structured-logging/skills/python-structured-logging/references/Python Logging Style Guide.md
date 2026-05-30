## Python Logging Style Guide

This guide defines best logging practices for Python services in general.

Prefer `structlog` when the project already uses it or can adopt it safely, because bound context, structured fields, and processor-based rendering fit these rules naturally. When a project intentionally uses only the standard library `logging` module, apply the same event design and field naming rules there with `extra=` or the project adapter.

## Table of Contents

1. Purpose of Logs
2. Basic Principle: One Log = One Event
3. Message Format: `event` Should Be Short and Stable
4. All Variable Data - Only in Fields
5. Field Names Should Be Consistent Across the Team
6. Bind Context Once, Do Not Pass It Manually to Each Log
7. Choose Logging Levels by Meaning, Not "by Feeling"
8. Do Not Log the "Start and End" of Every Function
9. Log Errors as Events with Cause and Context
10. Do Not Duplicate the Exception in Text if the Traceback Is Already There
11. Do Not Swallow the Cause of the Error Behind Generic Words
12. The Log Should Answer the Question "What Happened," Not "What the Developer Thinks"
13. Do Not Log Secrets or Sensitive Data
14. Log Payload Selectively and Deliberately
15. Success Events Are Also Important, But Only If Operationally Useful
16. For Long-Running Operations, Log the Result and Duration
17. For Retries and Degradations, Log Separate Attributes
18. Separate Business Events from Technical Events
19. Do Not Use the Root Logger as a General Dump
20. Canonical Record Template

### 1. Purpose of Logs

Logs are meant to answer three questions: what happened, in what context did it happen, and what to do next. Therefore, each message should describe a specific event, and the details of the event should be conveyed as separate fields, not hidden in the text. This approach aligns with structured logging in general. In `structlog`, context usually accumulates via `bind()` or `contextvars`; in stdlib `logging`, the same shape is usually carried with `extra=` or a logger adapter. ([structlog][1])

### 2. Basic Principle: One Log = One Event

Write a log as an event, not as a developer's comment. The message should be short, stable, and consistent across services. A good model is `event` as the name of what happened, while all variable information goes into fields. Structlog’s event-dictionary model encourages a small number of meaningful, context-rich records instead of scattered narrative logs. ([structlog][5])

Preferred `structlog` style:

```python
logger.info(
    "user_authenticated",
    user_id=user.id,
    auth_method="oauth",
    request_id=request_id,
)
```

Acceptable stdlib `logging` style:

```python
logger.info(
    "user_authenticated",
    extra={
        "user_id": user.id,
        "auth_method": "oauth",
        "request_id": request_id,
    },
)
```

Incorrect:

```python
logger.info(f"User {user.id} authenticated via oauth, request={request_id}")
```

In the second option, the data is mixed with the string, making it harder to search, filter, and aggregate. Both `structlog` and stdlib `logging` support carrying event data separately from the message text. ([structlog][5], [Python docs][3])

### 3. Message Format: `event` Should Be Short and Stable

The event text should be:

* in `snake_case`;
* without variable values;
* without punctuation at the end;
* without emotional phrasing;
* the same for the same situations.

Recommended style:

```python
"user_created"
"url_redirect_failed"
"broker_publish_started"
"db_transaction_committed"
```

Not recommended:

```python
"User created successfully!"
"Failed to redirect url 123"
"Something went wrong"
"Start processing..."
```

The point is that `event` is the name of the event class, not a story. The stdlib logging model and `structlog`’s event-dictionary model both work best when the message names the event clearly and the details live in structured fields. ([Python docs][4], [structlog][5])

### 4. All Variable Data — Only in Fields

Convey any event details as separate keys:

* identifiers;
* error codes;
* state;
* durations;
* attempt counts;
* sizes, amounts, statuses;
* external dependencies.

Example:

```python
logger.warning(
    "retry_scheduled",
    operation="send_email",
    attempt=3,
    max_attempts=5,
    delay_seconds=10,
)
```

Do not write like this:

```python
logger.warning("Retry scheduled: send_email, attempt 3/5, delay 10s")
```

The reason is simple: structured fields are indexed and filtered much better than text. `structlog` explicitly supports rendering event dictionaries to JSON, and stdlib `logging` supports contextual fields via `extra` and adapters. ([structlog][5], [Python docs][3])

### 5. Field Names Should Be Consistent Across the Team

The most common problem with team logs is that the same thing is called differently: `user_id`, `userid`, `uid`, `customer_id`. This should not happen.

Basic rules:

* `snake_case` for all keys;
* one meaning — one name;
* do not use abbreviations unless necessary;
* units explicitly in the field name;
* entity IDs always end with `_id`.

Recommended dictionary:

```python
request_id
trace_id
span_id
user_id
session_id
order_id
task_id

duration_ms
timeout_seconds
size_bytes
attempt
max_attempts

status
reason
error_code
http_method
http_status
db_host
broker_topic
```

It is especially useful to define “canonical” fields in advance that will appear in almost every service. This follows directly from the idea of centralized structured logging: a common field dictionary greatly simplifies search and correlation. ([structlog][5], [Python docs][3])

### 6. Bind Context Once, Do Not Pass It Manually to Each Log

For data that lives within a request, task, or worker, use context binding. In `structlog`, this usually means a bound logger or `contextvars`. In stdlib `logging`, this usually means a logger adapter, request middleware, filter, or other project-level mechanism that injects shared fields consistently. For request-scoped data, this is preferable to manually repeating `request_id=...` in every line. ([structlog][1])

Example:

```python
log = logger.bind(request_id=request_id, user_id=user_id)
log.info("profile_update_started")
log.info("profile_update_finished")
```

Or via request-local context:

```python
structlog.contextvars.bind_contextvars(
    request_id=request_id,
    user_id=user_id,
)
```

This produces two effects: less duplication and higher consistency. ([Python docs][3])

### 7. Choose Logging Levels by Meaning, Not “by Feeling”

The level should reflect the operational significance of the event.

`DEBUG` — diagnostic details for development and local debugging. In production this is usually noise.

`INFO` — expected business or system events: task start, successful processing, message publication, operation completion.

`WARNING` — the situation is abnormal, but the system is still coping: retry, fallback, degradation, partially lost context, slow response, non-critical failure of an external service.

`ERROR` — a specific operation failed: a request crashed, a record was not saved, a message was not sent.

`CRITICAL` — the service cannot continue normal operation or there is a risk of data loss or unavailability. This matches the stdlib logging level semantics. ([Python docs][4])

A practical rule: if an incident does not require immediate attention from an on-call engineer, it is almost never `CRITICAL`.

### 8. Do Not Log the “Start and End” of Every Function

Logs like “entered function”, “exit function”, “processing”, “step 1”, “step 2” almost always create noise. Prefer a smaller number of canonical, context-rich events that describe meaningful state transitions. ([structlog][5])

Bad:

```python
logger.debug("start validate")
logger.debug("start save")
logger.debug("start publish")
logger.debug("done")
```

Better:

```python
logger.info(
    "order_processed",
    order_id=order.id,
    validation="passed",
    persisted=True,
    published=True,
    duration_ms=duration_ms,
)
```

The exception is truly complex areas where intermediate steps are important for diagnostics and do not duplicate each other.

### 9. Log Errors as Events with Cause and Context

For errors, you need not just the exception text, but context:

* what operation was being performed;
* for which entity;
* in an external dependency or internally;
* will the error affect the user;
* will there be a retry.

Use `logger.exception(...)` inside `except` when a traceback is needed. `structlog` documents `exception()` and structured tracebacks, and stdlib `logging` supports exception-aware logging APIs as well. ([structlog][6], [Python docs][4])

Correct:

```python
try:
    await broker.publish(message)
except BrokerTimeoutError:
    logger.exception(
        "broker_publish_failed",
        topic=topic,
        message_id=message_id,
        retryable=True,
    )
```

Incorrect:

```python
except Exception as e:
    logger.error(f"Publish failed: {e}")
```

Why the second option is bad:

* the failure type as a separate field is lost;
* no operation context;
* the traceback may not end up in the log;
* the string is harder to aggregate.

### 10. Do Not Duplicate the Exception in Text if the Traceback Is Already There

If you do `logger.exception("db_query_failed", query_name="get_user")`, do not write `error=str(exc)` just because “that’s how it’s done.” Do this only if it is a short, useful, stable attribute that is really needed for filtering. Otherwise, you get duplication of the same information in different forms.

Good:

```python
except UniqueViolationError:
    logger.exception(
        "user_create_failed",
        reason="duplicate_email",
        email_domain=email_domain,
    )
```

Restraint is important here: a structured traceback already contains many details, and the official structlog documentation specifically emphasizes that structured exception tracebacks are convenient precisely for machine analysis. ([structlog][6])

### 11. Do Not Swallow the Cause of the Error Behind Generic Words

Prohibited formulations for `event`:

* `error`
* `unexpected_error`
* `something_went_wrong`
* `exception`
* `failed`

The word `failed` is allowed only as part of a specific event, for example `cache_write_failed` or `payment_capture_failed`. Generic events like `error` or `something_went_wrong` are weak because they do not describe the operation that failed. ([Python docs][4])

### 12. The Log Should Answer the Question “What Happened,” Not “What the Developer Thinks”

Avoid:

* jokes;
* emotional assessments;
* colloquial phrases;
* exclamations;
* evaluative comments.

Bad:

```python
logger.error("Well, the database died again")
logger.warning("Strange, but it seems to have worked")
```

Good:

```python
logger.error("db_connection_failed", db_host=db_host, retryable=False)
logger.warning("fallback_used", provider="cache", source="stale_data")
```

### 13. Do Not Log Secrets or Sensitive Data

Logs should not contain:

* passwords;
* tokens;
* cookies;
* authorization headers;
* full card numbers;
* full personal data without necessity;
* raw payloads entirely by default;
* raw request/response body by default.

This is not a unique structlog recommendation, but a general operational and security baseline. Structured logging is even more dangerous here than string logging because data is easier to index and propagate across systems, so the composition of bound or injected fields must be controlled carefully. ([structlog][1], [Python docs][3])

Practice:

* log `user_id`, but not the entire email unless necessary;
* log `email_domain`, but not the full address;
* log `card_last4`, but not the PAN;
* log the payload size, but not the entire payload.

### 14. Log Payload Selectively and Deliberately

If you need to log input data, choose the minimally sufficient slice:

* key identifiers;
* operation type;
* size/count of elements;
* whitelisted fields.

Do not:

```python
logger.info("webhook_received", payload=payload)
```

Better:

```python
logger.info(
    "webhook_received",
    event_type=payload["type"],
    object_id=payload["object"]["id"],
    item_count=len(payload.get("items", [])),
)
```

### 15. Success Events Are Also Important, But Only If Operationally Useful

Do not log every successful getter/setter. You should log:

* start/end of a background task;
* completion of a business operation;
* publication to an external system;
* successful fallback;
* process state changes.

That is, `INFO` should show vital system transitions, not every mechanical step. This aligns with the general goal of reducing noise and keeping only the most informative events. ([structlog][5], [Python docs][4])

### 16. For Long-Running Operations, Log the Result and Duration

If an operation can be slow, a log without duration is almost useless.

Correct:

```python
logger.info(
    "report_generated",
    report_id=report_id,
    duration_ms=duration_ms,
    row_count=row_count,
)
```

Even better is to have a consistent unit suffix: `duration_ms`, `size_bytes`, `timeout_seconds`.

### 17. For Retries and Degradations, Log Separate Attributes

A retry is not just a warning/error, but an important part of system behavior. Useful fields:

* `attempt`
* `max_attempts`
* `delay_seconds`
* `retryable`
* `reason`
* `dependency`

Example:

```python
logger.warning(
    "http_request_retry_scheduled",
    dependency="billing_api",
    attempt=2,
    max_attempts=5,
    delay_seconds=1.5,
    reason="timeout",
)
```

### 18. Separate Business Events from Technical Events

This is one of the most useful agreements for a team.

Business events:

* `payment_captured`
* `subscription_renewed`
* `url_shortened`

Technical events:

* `db_query_failed`
* `cache_miss`
* `http_client_timeout`
* `broker_publish_failed`

They coexist but should not be confused. Then logs can be read at two levels: “what happened in the product” and “what happened in the infrastructure.”

### 19. Do Not Use the Root Logger as a General Dump

Even if you will discuss configuration separately later, it is worth establishing the style rule now: the logger should be modular and predictable, not falling into an unnamed root. The Python docs recommend module-level loggers that follow the package hierarchy. ([Python docs][4])

### 20. Canonical Record Template

For most events, a good template is:

```python
logger.<level>(
    "<event_name>",
    object_id=...,
    status=...,
    reason=...,
    duration_ms=...,
    request_id=...,
)
```

Where:

* `<event_name>` — short, stable event name;
* required IDs — only those really needed;
* `status` and `reason` — if there is branching;
* `duration_ms` — for operations where performance matters;
* request/task context — via bind/contextvars, not manually inline.

---

## Short Summary of Rules for the Team

1. Log events, not stories.
2. `event` — short, stable, in `snake_case`.
3. Pass variable data only as separate fields.
4. Do not use f-strings or concatenation for significant log data.
5. Bind common context via `bind()` or `contextvars`, or inject it consistently in stdlib `logging`.
6. Reduce noise: fewer intermediate logs, more final “canonical” ones.
7. `ERROR` — an operation failed; `CRITICAL` — the service is at risk.
8. For exceptions, use `logger.exception(...)` with operation context.
9. Do not write “something went wrong.”
10. Do not log secrets, tokens, or unnecessary payloads.
11. Field names must be consistent across the entire project.
12. The log should be useful for search, filtering, and correlation.

---

## Mini Examples: Bad / Good

Bad:

```python
logger.error(f"Failed to save user {user.id}: {e}")
```

Good:

```python
logger.exception(
    "user_save_failed",
    user_id=user.id,
    operation="create",
)
```

Bad:

```python
logger.info("Starting request processing")
logger.info("Fetching user")
logger.info("Checking permissions")
logger.info("Done")
```

Good:

```python
logger.info(
    "request_processed",
    request_id=request_id,
    route=route_name,
    user_id=user_id,
    authorized=True,
    duration_ms=duration_ms,
)
```

Bad:

```python
logger.warning("Something looks odd")
```

Good:

```python
logger.warning(
    "cache_fallback_used",
    cache_key=cache_key,
    reason="redis_unavailable",
)
```

[1]: https://www.structlog.org/en/stable/bound-loggers.html "Bound Loggers"
[3]: https://docs.python.org/3.12/howto/logging-cookbook.html "Logging Cookbook"
[4]: https://docs.python.org/3/library/logging.html "logging — Logging facility for Python"
[5]: https://www.structlog.org/en/stable/getting-started.html "Getting Started"
[6]: https://www.structlog.org/en/stable/exceptions.html "Exceptions"
