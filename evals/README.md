# Behavioral evaluations

These cases evaluate agent decisions separately from deterministic repository checks. They have not been benchmarked yet. `cases.json` contains prompts, input files, expected implicit activation, and outcome criteria. Keep cases and results outside the installed skill so the agent does not see the grading answers.

For a complete generated HTTP application with before/after checks, see the [FastAPI demo](demo/README.md).

## Decision coverage

Compare `event_contract` with `event_contract_discovery`: the former explicitly states the contract, while the latter leaves event consumers in the project for the agent to discover. `local_change_scope` checks whether a single-field request stays local and whether verification claims match the captured boundary. `wrapper_api` exercises a mapping-based facade rather than a standard logger API.

`indirect_context_activation` asks for correlation without naming logging or the skill. Together with `unrelated_python_with_logging` and `unrelated_cli`, it probes both missed activation and false positives. Inspect skill-load traces rather than inferring activation from the final code. These are unbenchmarked scenarios, not evidence of improved activation.

## Run a case

1. Create a fresh temporary project and copy only the listed fixtures into it, keeping their basenames. Install any fixture dependencies in an isolated environment. Record initial file checksums.
2. Start a fresh agent session with no prior discussion of the expected solution. Use the exact prompt from the case. For activation tests, make the skill discoverable without naming it in the prompt. Inspect the trace to determine whether it was loaded.
3. Allow local edits and tests only in the temporary project. These cases need no production services, real credentials, publishing, or network access beyond dependency setup.
4. Save the trace, final response, diff, emitted logs, and test output. Score each criterion with evidence; do not grade exact wording or prescribed code structure. Use runtime checks for output and behavior, and human review for scope and diagnostic usefulness.
5. Repeat in a separate clean context without the skill installed or available through another plugin. Do not force skill invocation in the baseline. Use the same model, runtime, prompt, dependencies, and permissions.

Run at least three trials per case and condition when making quality claims. Also compare the old and new skill revisions if evaluating an instruction change. Explicit invocation can be tested separately, but cannot establish implicit activation accuracy. Models may need different amounts of guidance; report results per model instead of pooling them.

## Record results

Use a JSONL row per trial with these fields:

```json
{"case_id":"stdlib_refactor","condition":"with_skill","skill_commit":"<sha>","model":"<exact-model>","runtime":"<client-version>","trial":1,"skill_loaded":true,"criteria":[{"index":0,"passed":true,"evidence":"<artifact-path-and-observation>"}],"elapsed_seconds":0,"input_tokens":null,"output_tokens":null,"artifacts":"<temporary-run-directory>"}
```

Use null for unavailable metrics; do not infer them. Mark unresolved criteria as null with an explanation, rather than passing them. Summarize per-case pass rates, activation misses/false positives, latency, and token usage where available. Compare paired outcomes with and without the skill. Store results outside the skill package; no generated results are committed by the deterministic checks.

The unit tests in `tests/` verify the bundled examples and repository validator. They do not execute an agent or prove that it passes these scenarios.
