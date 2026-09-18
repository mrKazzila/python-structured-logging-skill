# Python Logging Integration Notes

Read the section relevant to the current stack or failure mode. Shared scope and naming rules live in `SKILL.md`.

## Output pipeline

Stdlib `extra` adds attributes to a LogRecord; a default text formatter does not include arbitrary attributes. Inspect the project's formatter before claiming the output is structured. Preserve the existing handler configuration; reusable modules should not call `basicConfig()` or install root handlers.

Use `extra={"invoice_id": invoice_id}` with stdlib, and `invoice_id=invoice_id` with structlog. Do not use reserved LogRecord keys such as `name`, `message`, or `levelname` as `extra` fields. Formatter-required fields must also be handled for third-party records that lack them.

Capture the final rendered output as well as records. Check JSON decoding where JSON is the configured format, field types, exception rendering, and duplicate records from handler propagation. A test that only captures the pre-render event dictionary cannot establish downstream compatibility.

## Context lifecycle

`logger.bind(...)` returns a logger with additional context; pass that logger to code that needs it. It does not automatically enrich independent loggers elsewhere.

For a structlog application already using contextvars, check that `merge_contextvars` is in the processor chain. Clear context at the start of a request/job, then bind its identifiers. Reset or clear context when the operation ends, including failure paths. Use scoped binding/token reset for nested operations that must restore parent context instead of clearing it.

Test two overlapping requests with distinct IDs and a subsequent operation with no ID. Their outputs must not share identifiers. Thread/task boundaries and hybrid sync/async frameworks may require explicit propagation; do not assume every execution context shares the same values.

For stdlib, retain the existing adapter, filter, or record factory. Check the supported Python version and adapter behavior before relying on per-call `extra` merging.

## Exception ownership and sensitive output

Choose the owner based on the call chain: a request boundary, worker, or command may already record failures. Adding another exception log below it can duplicate alerts. If a lower layer owns the only failure record and propagates the exception, document that its caller must not log it again.

`logger.exception` normally renders the exception message too. Allowlisting structured fields alone does not sanitize credentials embedded in a URL, exception text, or captured locals. Exercise the configured sanitizer with synthetic sensitive values and inspect its final output. Never use real secrets as fixtures.

The paired examples use a non-retryable negative amount to illustrate preserved behavior. Both versions raise the same exception for the same input. The good version changes logging only; it does not add retry logic or invent payment metadata.

## Event contracts and migration

Before renaming an event, inspect repository-owned dashboards, alerts, queries, and tests when available. Keep existing conventions such as dotted events when the task does not authorize a schema migration. If downstream consumers are external and cannot be checked, report that limitation.

For requested migrations, explain old-to-new names and consumer updates. Diagnostic prints can become logs; intentional CLI results must remain on the expected output stream.

## Sources

- [Python logging API](https://docs.python.org/3/library/logging.html)
- [Python logging cookbook](https://docs.python.org/3/howto/logging-cookbook.html)
- [structlog context variables](https://www.structlog.org/en/stable/contextvars.html)
