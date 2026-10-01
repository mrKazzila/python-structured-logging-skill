# Deliberately defective worker snapshot

These four files preserve the reviewed stdlib worker from
`/private/tmp/logging-skill-review-20260925/app` on 2026-09-25. The remaining app
files are unchanged demo template files. This is a regression fixture, not a
recommended implementation. It is never copied by `demo.py create`.

The old evaluator accepted it (11/11). The new runtime checks reject its unsafe
Uvicorn output, duplicate failure ownership, NaN formatter diagnostic fallback,
and missing correlation header on unexpected 500 responses.

`test_minimal_reviewed_worker_repairs_pass` applies corrections only to a temporary
copy: finite-value normalization, server logging configuration, and an outer
HTTP failure/correlation boundary with one failure owner. The snapshot stays
intentionally defective. See `../../runtime-regressions.md` for evidence.
