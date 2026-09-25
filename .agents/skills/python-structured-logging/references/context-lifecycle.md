# Context lifecycle

`logger.bind(...)` returns a logger with additional context; pass that logger to code that needs it. It does not automatically enrich independent loggers elsewhere.

For a structlog application already using contextvars, check that `merge_contextvars` is in the processor chain. Clear context at the start of a request/job, then bind its identifiers. Reset or clear context when the operation ends, including failure paths. Use scoped binding/token reset for nested operations that must restore parent context instead of clearing it.

Test two overlapping requests with distinct IDs and a subsequent operation with no ID. Their outputs must not share identifiers. Thread/task boundaries and hybrid sync/async frameworks may require explicit propagation; do not assume every execution context shares the same values.

For stdlib, retain the existing adapter, filter, or record factory. Check the supported Python version and adapter behavior before relying on per-call `extra` merging.
