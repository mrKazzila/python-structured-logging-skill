# Worker/consumer evaluation

Independent non-HTTP stdlib fixture. `template/` is a deliberately flawed logging baseline;
its business contracts are valid. `reference/` + `repair.py` are evaluator calibration only.
No third-party dependencies. Python >=3.11.

```sh
python3 -m unittest discover -s tests/worker_consumer -v
python3 evals/worker_consumer/evaluate.py /absolute/candidate /tmp/new-report.json
```

Exit 0 = all criteria pass, 1 = observable defect; execution/setup errors raise separately.
Reports are created exclusively, not overwritten. Each scenario runs in a fresh isolated
Python subprocess; stdout/stderr are OS-level captured and metadata uses a separate file.
Never infer failure ownership from passing safety or vice versa. No weighted score.

Frozen criteria before A/B:

| Check | Observable boundary |
|---|---|
| business_contract | result values, original payloads, dependency calls and exact exceptions |
| retry_ack_contract | success ack, retry request, attempt limit DLQ, poison DLQ, unchanged unexpected propagation and runtime retry |
| cancellation_contract | CancelledError propagation; no disposition |
| whole_runtime_json | all captured runtime streams parse as strict JSON objects |
| payload_credential_exception_safety | synthetic payload/token/exception sentinels absent |
| concurrent_nested_context | overlapping dependency operations retain each message/correlation; nested operation restores parent |
| context_cleanup | post-success/failure/cancellation in same task; nested scope restoration |
| event_contracts | preserved four documented event names, count and originating IDs |
| single_failure_ownership | one warning/error or semantically named failure/retry/DLQ diagnosis per failed attempt |
| background_failure | pending tasks drained and audit failure owned/correlated once |
| cancellation_level | no false cancellation ERROR |
| outcome_fields_units | attempt/outcome, amount_cents, optional nonnegative duration_ms |
| bounded_events_noise | stable events; <=14 operational non-DEBUG events for 9 attempts + audit + lifecycle allowance |
| formatter_nonfinite/object/key/cycle | public facade does not raise, leak, emit raw fallback or invalid JSON; safe diagnostic and subsequent event both present |

Calibration includes a known bad baseline, minimal repaired reference, observable mutations
(strict JSON, silent drop, propagation, runtime plaintext, credential leak, extra ack), and
acceptance of implementation-independent structured fallback and absent optional lifecycle.
No private logging helper names are inspected. Facade test events are excluded from noise.
Safe field omission/placeholder/fallback are all accepted; diagnostic spelling is unconstrained.
Fixed noise threshold is project-specific, not a universal skill rule. Foreign runtime logs
must satisfy the fixture's JSON contract; intentional CLI output is not part of this fixture.

Limitations: synthetic finite batches and fake dispositions, no broker integration, crash
redelivery, real rebalance, process signals, queue-based logging, sink I/O outages, or performance
measurement. Unsupported value probes cover representative inputs, not an exhaustive serializer.
No requirement for arbitrary unlabelled string redaction outside documented sensitive fields.
A single cross-domain pair is exploratory, not statistical causal evidence.
