[group('Quality')]
[doc('Validate skill metadata, resources, and plugin paths')]
validate:
    @uv run --with-requirements requirements-dev.txt python scripts/validate_repo.py

[group('Quality')]
[doc('Run example and validator regression tests')]
test:
    @uv run --with-requirements requirements-dev.txt python -m unittest discover -s tests -v

[group('Quality')]
[doc('Run all deterministic checks')]
check: validate test
    @python3 scripts/check_release_state.py

[group('Quality')]
[doc('Test both generated FastAPI demo variants and the external evaluator')]
demo-test:
    @uv run --with-requirements evals/demo/requirements-structlog.txt python -m unittest discover -s tests/demo -v
