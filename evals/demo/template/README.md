# Order API logging demo

This is an intentionally flawed local training application. Improve its logging while keeping the HTTP behavior and existing logging stack. All credentials are synthetic. There are no external provider calls or database dependencies.

## Setup and run

Requires Python 3.12+:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

On Windows use `.venv\Scripts\python.exe`. The server is optional: contract and external evaluation tests use an in-process ASGI transport. Interactive API documentation is at `http://127.0.0.1:8000/docs`.

## Existing contracts

- `GET /health`: 200, `{"status":"ok"}`.
- `POST /orders`: body with nonempty `order_id`, positive integer `amount_cents`, optional `provider_mode` (`success` by default or `timeout`), and optional synthetic `payment_token`.
- Success: 201, `{"order_id":"<input>","status":"created"}`. Provider timeout: 503, `{"detail":"provider unavailable"}`. Invalid input: 422.
- Each response returns `X-Request-ID`: preserve a supplied value or generate one if absent.
- Consumers rely on `order.created`, `order.failed`, and `request.completed`. Preserve these names. The success event needs `order_id` and `amount_cents`; the failure event needs `order_id`, `retryable=true` (the simulated timeout is transient), error diagnostics, and traceback. Request completion needs `status_code` and request correlation.
- Emit JSON logs with `event` and `level`, including `request_id` for request-scoped records. Context must not cross requests or remain after a request completes. The logging facade `app.observability` is also used outside requests.
- Keep the facade's `configure`, `bind_request`, `reset_request`, `info`, and `exception` entrypoints, and the importable `app.main.app`. Their implementations may change.
- Keep `app.provider.charge(order)` callable with an object exposing the documented order fields. Its success result and `ProviderTimeout` exception type/message are business contracts, checked independently from log output.
- Preserve provider behavior, HTTP results, and the selected logging stack. Never log synthetic credentials from bodies, headers, or exception messages. Fix sanitization in the logging pipeline without altering the provider exception.

The public tests cover business behavior only and already pass in the original project. An external evaluator checks logging after you finish. Do not modify `demo.json`, dependency pins, or public contract tests to make evaluation pass. Add your own tests as needed.

## Task for the agent

Use the text in `PROMPT.md` in a fresh agent session rooted in this directory. For a skill-enabled run, make the repository's logging skill available in your client. For a baseline, use a clean client configuration without that skill or a plugin that bundles it. Generating this project does not install or disable any skills.
