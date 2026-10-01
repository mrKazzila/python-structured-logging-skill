# Exception ownership and sensitive output

Choose the owner based on the call chain: a request boundary, worker, or command may already record failures. Adding another exception log below it can duplicate alerts. If a lower layer owns the only failure record and propagates the exception, document that its caller must not log it again.

`logger.exception` normally renders the exception message too. Allowlisting structured fields alone does not sanitize credentials embedded in a URL, exception text, or captured locals. Exercise the configured sanitizer with synthetic sensitive values and inspect its final output. Never use real secrets as fixtures.

The paired examples use a non-retryable negative amount to illustrate preserved behavior. Both versions raise the same exception for the same input. The good version changes logging only; it does not add retry logic or invent payment metadata.
