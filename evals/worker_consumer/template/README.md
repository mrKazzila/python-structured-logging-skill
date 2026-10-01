# Async payment message consumer

Python 3.11+, stdlib only. Run `python3 -m unittest discover -s tests -v`.
Architecture: fake Broker -> Consumer.handle -> service.process -> Dependency.execute.
Runtime concurrently dispatches a batch and drains audit tasks at shutdown. No HTTP.

Public contracts:
- Message(message_id, correlation_id, payload, attempt=1). IDs are approved opaque identifiers.
  Payload includes amount_cents, mode, optional audit_fail, and sensitive payment_token/body.
  Preserve the payload object and content; no new required fields or validation semantics.
- Success returns {message_id, amount_cents}, acknowledges once, starts one audit task.
- RetryableError before attempt 3 retries once and returns 'retry'; attempt >=3 dead-letters once.
  The fake broker records a retry request; it does not automatically redeliver.
- PoisonError dead-letters once and returns 'dead_letter'.
- Unexpected exceptions propagate unchanged from handle (no ack there); runtime.run requeues once.
- Cancellation propagates, leaves message unacked, and is normal shutdown, not an error.
- Audit tasks are drained even when they fail; audit failure must not change an existing ack.
- Dependency results, call counts, exception types and messages are business contracts.
- Public logging facade entrypoints stay available; nested scope must restore parent bindings.

Logging contracts:
- Keep stdlib and architecture. Configure output in the composition/facade setup.
- Complete runtime stdout/stderr must contain JSON log objects with string event and level.
  Every operational failure needs one safe diagnostic owner, including audit failures.
- Events consumed by operations: message.processed, message.retry, message.dead_letter, audit.failed.
  Keep their meanings. Include message_id, correlation_id, attempt on message outcomes and
  outcome ('ack', 'retry', 'dead_letter', 'failed') where relevant. Money uses amount_cents.
- Diagnostics must not reveal raw payload, credentials, exception messages or source secrets.
  Arbitrary structured values must not make logging raise or fall through to raw diagnostics.
- Stable bounded event names; put IDs in fields. Optional duration must use explicit units.
- Aim for one operational outcome per attempt; DEBUG diagnostics are welcome. No requirement
  for an INFO arrival/service event. Startup/shutdown summaries are optional and useful once/batch.
- Concurrent messages must stay isolated. Restore context after success, failure, cancellation,
  and nested scopes. Background audit records must retain their originating IDs.

All secrets in this fixture are synthetic. Improve logging only; no broker/server dependency needed.

`python3 -m consumer` runs the normal bootstrap: adapter stdlib logging configuration,
then facade configure(), then runtime.run(). The evaluator uses the same order.
The fake adapter represents a finite assigned batch; no real broker rebalance protocol is claimed.
