# FastAPI logging demo evaluation

Generate disposable projects for manual agent trials in either stdlib logging or structlog. Business code is shared; only the logging backend and pinned dependencies differ. The templates intentionally contain logging defects. They are not deployment examples and are not bundled with the installed skill.

## One trial

From this repository:

```sh
python3 scripts/demo.py create --stack stdlib --dest /tmp/logging-demo-stdlib
python3 -m venv /tmp/logging-demo-stdlib/.venv
/tmp/logging-demo-stdlib/.venv/bin/python -m pip install -r /tmp/logging-demo-stdlib/requirements.txt
(cd /tmp/logging-demo-stdlib && .venv/bin/python -m unittest discover -s tests -v)
```

From this repository, evaluate:

```sh
python3 scripts/demo.py check --project /tmp/logging-demo-stdlib --report /tmp/stdlib-before.json
# Run the agent manually in /tmp/logging-demo-stdlib using PROMPT.md.
python3 scripts/demo.py check --project /tmp/logging-demo-stdlib --report /tmp/stdlib-after.json
```

Repeat with `--stack structlog` and a different project/report path. The initial check is expected to exit 1: the HTTP contract works, but logging defects are present. An improved project should exit 0. Exit 2 means a setup/probe error, not a failed logging criterion. Reports are created exclusively and are never overwritten; choose a new filename for each run. Setup errors are recorded with `passed: null` when a report can be created.

`check` executes the generated application's code in a subprocess using its `.venv`, with a 60-second timeout. It does not install dependencies or edit application files. This is process isolation, not an operating-system security sandbox. Both output streams are captured, and only synthetic credentials are used.

## What is measured

The report includes dependency/Python versions, HTTP observations, rendered logs, backend call counts, and a pass/fail result with evidence for each criterion:

- HTTP responses and request ID response headers.
- Provider return values and original exception type/message, checked directly so changing business exceptions cannot substitute for safe log rendering.
- JSON output, stable event names, existing event contracts, and emitted structured fields.
- Exactly one error record per failed order with traceback and error type.
- No synthetic secrets anywhere in stdout or stderr, including exception rendering.
- Correct correlation for overlapping requests and cleanup after successful, invalid, and failed requests.
- Runtime use of the selected logging backend. This probe observes Python logging/structlog emission calls; it is not a general proof against adversarial code or dependency migration.

Probe events are emitted outside the request in the same coroutine, so task teardown cannot mask missing cleanup. Concurrency is deterministic: the provider yields control without using timing delays or external services.

Compare `criteria` by `id` in the before/after JSON reports. Raw observations make failures inspectable. HTTP contract failures must not be traded for better logging scores. Do not claim agent activation from these checks: confirm skill loading separately in the agent trace.

## Skill versus no skill

Use two clean generated projects, the same model/client/dependencies, the same task text, and fresh sessions. Ensure the baseline client does not discover a globally installed skill or bundled plugin. The generator does not manage client configuration. Use the skill folder from this repository rather than an older installed copy. Keep evaluation sources and reference repairs out of the agent workspace; they are never copied by `create`.

The external evaluator is held out by workspace separation, not by secrecy against a deliberately searching agent. The public README discloses behavioral contracts; graders test those contracts rather than a preferred implementation. Follow the trial-recording guidance in [the evaluation guide](../README.md) for repeated runs and model/skill version attribution. No agent benchmark results are claimed by the demo's CI.

## Maintainer checks

```sh
just demo-test
```

CI tests both dependency environments independently. Checks verify that original templates reproduce known failures, reference repairs pass every criterion, and individual regressions are detected. Reference files are test oracles and are not distributed to generated projects. The demo redactor handles synthetic credential markers only; it is not a production secret detection library.

Dependencies are pinned in the two `requirements-*.txt` files. Their corresponding `.in` files specify direct requirements. Regenerate with `uv pip compile --python-version 3.12` after an intentional dependency update and rerun both variants.
