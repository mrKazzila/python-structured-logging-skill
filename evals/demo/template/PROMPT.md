Improve logging in this FastAPI order API. Inspect the existing stack and README contracts first. Preserve the HTTP behavior, provider exception behavior, public logging facade, and existing event names consumed by alerts. Keep the current logging stack.

Make the rendered logs structured and useful, remove duplicate failure records, protect credentials including those in exception text, and ensure request context remains correct during overlapping requests and is cleaned up afterward. Use synthetic data only. Run the business tests and add focused checks of the actual output. Explain the changes and verification performed.

Do not change the demo manifest, dependency pins, or existing contract tests. You may add tests. Work only in this demo project.

For an explicit skill-enabled trial, prepend this sentence to the task above:

Use $python-structured-logging for this task.

For implicit activation trials, send only the task above, without that sentence. Use your client's invocation syntax if it differs from Codex's `$` syntax.
