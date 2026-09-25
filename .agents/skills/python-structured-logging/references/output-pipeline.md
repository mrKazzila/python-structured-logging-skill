# Output pipeline

Stdlib `extra` adds attributes to a LogRecord; a default text formatter does not include arbitrary attributes. Inspect the project's formatter before claiming the output is structured. Preserve the existing handler configuration; reusable modules should not call `basicConfig()` or install root handlers.

Use `extra={"invoice_id": invoice_id}` with stdlib, and `invoice_id=invoice_id` with structlog. Do not use reserved LogRecord keys such as `name`, `message`, or `levelname` as `extra` fields. Formatter-required fields must also be handled for third-party records that lack them.

Capture the final rendered output as well as records. Check JSON decoding where JSON is the configured format, field types, exception rendering, and duplicate records from handler propagation. A test that only captures the pre-render event dictionary cannot establish downstream compatibility.

At the application's configuration boundary, include framework/server/access/error/lifecycle loggers and the actual stdout/stderr or collector path, not just the application logger. Exercise an unexpected failure through that runtime: a safe application formatter is insufficient if another output path can emit raw data. Keep reusable modules free of global logging configuration.

Formatter failure is part of this safety boundary. Probe non-finite numbers, unsupported objects and cyclic structured values through the public logging API, including stdlib `handleError`/diagnostic fallback. Use bounded safe normalization or a safe structured fallback: logging must not raise into application code, disclose the original exception/source through fallback, or emit invalid JSON when JSON is the output contract. Capture both streams and verify that a subsequent event still emits; silent record loss is not a successful fallback.
