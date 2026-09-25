# Python Logging Integration Notes

Shared scope, event contracts, and naming rules live in [SKILL.md](../SKILL.md).
Read only the reference needed for the current change:

- [Output pipeline](output-pipeline.md): formatter/processor changes, missing fields, serialization, or duplicate handlers.
- [Context lifecycle](context-lifecycle.md): cross-module context, concurrent requests/jobs, or cleanup.
- [Exceptions and sensitive data](exceptions-and-sensitive-data.md): failure ownership or sanitizing rendered exceptions.

## Sources

- [Python logging API](https://docs.python.org/3/library/logging.html)
- [Python logging cookbook](https://docs.python.org/3/howto/logging-cookbook.html)
- [structlog context variables](https://www.structlog.org/en/stable/contextvars.html)
