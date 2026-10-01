# Runtime regression coverage

## Changes made / failure mapping

All four checks run from `scripts/demo.py check`; implementation is in
`runtime_probe.py` and `grading.py`. Regression test names below are in
`../../tests/demo/test_demo.py`.

| Criterion / test | Observable behavior | Why the old evaluator missed it |
| --- | --- | --- |
| `whole_process_output` / `test_reviewed_worker_whole_process_output` | Both actual process streams, including Uvicorn startup/error/access/shutdown, contain only JSON event/level objects and neither unique exception nor query secret. | ASGITransport never exercised Uvicorn handlers or access logging. |
| `unexpected_failure_ownership` / `test_reviewed_worker_duplicate_failure_ownership` | One error/critical event across application and server; raw Uvicorn exception reports also count. | Only handled provider failures and application output were checked. |
| `formatter_fallback_safety` / `test_reviewed_worker_formatter_fallback` | Public `log.exception` with an ordinary object, hostile non-string mapping key, cycle, NaN, +Infinity and -Infinity during an active secret-bearing exception neither raises nor produces raw diagnostics, secret, local sentinel, source marker, or invalid JSON. Every attempt emits a safe structured record or fallback, and a following public info call still renders. | Normal structured fields did not make the JSON encoder fail; the original NaN-only probe missed unsupported-key, object and cycle failures. |
| `unexpected_500_correlation` / `test_reviewed_worker_unexpected_500_correlation` | Actual HTTP 500 carries the supplied request ID, matching application `request.completed` with status 500. | Handled 503 and validation 422 did not exercise the outer framework error middleware. |

The fixture already promises JSON logs, no credentials in rendered exceptions,
one failure owner, and a request ID on **each response**. These checks enforce
those contracts; they do not introduce a universal rule that all frameworks must
add correlation headers to 500s. No skill instructions or production code were
changed. Corrections live exclusively in held-out reference fixtures and temporary
test projects.

## Before / After

The actual reviewed project was still available at
`/private/tmp/logging-skill-review-20260925`. It was re-evaluated unchanged before
editing the evaluator, then with the new checks:

| Implementation | Evaluator | Result |
| --- | --- | --- |
| Reviewed stdlib worker | Original | **11/11**, passed=true, exit 0 |
| Same worker | Extended | **11/15**, passed=false, exit 1 |
| Temporary minimally corrected worker | Extended | **15/15** |
| Positive reference, stdlib and structlog | Extended | **15/15** on each |

The compact machine-readable evidence is in
[`regressions/before-after.json`](regressions/before-after.json). Full local
reports were saved under `/tmp/logging-harness-evidence/before.json` and
`/tmp/logging-harness-evidence/after-runtime.json`; these temporary paths are not
required by the tests. The intentionally defective worker snapshot is preserved
in `regressions/reviewed_worker`, with hashes in the evidence file.

Observed failures on the unchanged worker:

- Both unique sentinels appeared: exception text in `uvicorn.error`, query in
  `uvicorn.access`. Plain Uvicorn records also violated the JSON contract.
- One application error plus one raw Uvicorn error reported the same request.
- NaN passed normalization but failed `json.dumps(..., allow_nan=False)`.
  stdlib printed `--- Logging error ---`, the original exception secret, and
  `FORMATTER_SOURCE_SENTINEL` from the public logging call's source line.
- HTTP status was 500; the response header was absent, while application failure
  and completion records carried the expected request ID.

`test_minimal_reviewed_worker_repairs_pass` verifies a corrected temporary copy.
`test_reference_repairs_pass_every_criterion` covers both supported backends.
`test_independent_runtime_source_regressions` then independently breaks server
configuration, failure ownership, finite-value normalization, and the outer
response header. For each backend and mutation, **only the corresponding new
criterion fails**. Thus the four checks are not aliases for one broad failure.

## Evaluator quality review

- **Implementation coupling:** the evaluator calls the documented logging facade,
  imports the public app, and registers an HTTP route using FastAPI's routing API.
  It does not call `_safe`, a formatter class, or application middleware internals.
  Private names occur only in a test-local patch of the frozen worker snapshot.
  An outer wrapper must expose its wrapped app through `.app` to permit route
  registration. Unsupported application shapes are setup errors, not passes.
- **Server fidelity:** real Uvicorn, h11, FastAPI/Starlette, lifespan, TCP, and an
  HTTP client are exercised. Uvicorn configures logging before importing the app,
  matching the documented CLI. No evaluator-installed redaction hides output.
  stdout/stderr are captured at the subprocess boundary; metadata uses a separate
  file. Cross-stream ordering is not assumed.
- **Timing/flakiness:** an explicit startup event replaces sleeps and polling;
  port 0 avoids a fixed-port race. The client, server coroutine, and subprocess
  have bounded timeouts. Shutdown completes before output is graded. Extreme CI
  slowness can still cause setup failures, which are reported as inconclusive.
- **Platform:** no shell server process, Unix signal, or fixed executable path is
  needed. Sandbox environments must permit loopback binding. Existing maintainer
  tests use virtualenv symlinks and may need privileges on Windows. This run
  verified macOS; Windows was not tested.
- **False positives:** JSON event/level and each-response headers are explicit
  fixture contracts. No particular exception formatting, private function names,
  arbitrary-object stringification, or access-event name is prescribed. Safe
  disabling of access logs is allowed. Server lifecycle prose is rejected because
  this fixture promises JSON output throughout the process.
- **False negatives:** safe normalization, field omission or a structured fallback
  may pass; silent dropping of an entire attempted event fails. Each synchronous
  call has descriptor-level stdout/stderr evidence, replayed into the complete
  process streams. Queued/asynchronous delivery is outside this fixture's current
  synchronous facade contract. Error ownership recognizes JSON error/critical levels and
  pinned Uvicorn's raw ASGI-error banner. Adversarial relabeling/dropping, alternate
  encodings of secrets, unrelated sink files, and custom background processes are
  outside this check. Unique per-run secrets prevent fixed-string redaction from
  appearing sufficient, but synthetic markers are not a general secret detector.
- **Duplication:** the old criteria remain separate for comparability. Runtime
  format/secrets, ownership, fallback, and correlation have distinct evidence and
  isolated source mutation controls. One real defect may legitimately violate
  several contracts; results are not statistically independent scores.

## Final assessment

The evaluation now closes the real-server output boundary, formatter diagnostic
fallback, and framework-generated 500 correlation gaps. Updating `SKILL.md` is
not necessary to enforce these existing rules.

Remaining risks include non-h11 protocols, multiple workers, streaming responses
that fail after headers/body start, background tasks, exception groups/chains,
other nonserializable fields, production `logging.raiseExceptions=False`, and
application-specific logging launch configurations. Startup failures are setup
errors rather than scored logging failures.

Next high-value improvements:

1. Exercise streaming/background-task errors and cancellation through real server
   pipelines, with explicit ownership and post-response semantics.
2. Add a serialization matrix (Infinity, nested fields, unsupported objects,
   exception chains/groups) and both stdlib diagnostic modes.
3. Extend concurrent real-HTTP correlation tests to generated IDs and nested
   context restoration, plus supported worker/protocol configurations.

Reproduce maintained checks with `just demo-test`. No commits are made by these
checks or by this change.
