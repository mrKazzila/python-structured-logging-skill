# Copy this file to just/local.just if you want maintainer-only release commands locally.

[group('Release')]
[doc('Validate skill release state and manifest consistency')]
release-check:
    python3 scripts/check_release_state.py

[group('Release')]
[doc('Run release preflight checks for a target version (x.y.z)')]
release-preflight version:
    @echo "==> release preflight for {{version}}"; \
    if [[ ! "{{version}}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then \
        echo "Version must match x.y.z (without 'v' prefix)." >&2; \
        exit 1; \
    fi; \
    echo "==> ensure branch is up to date"; \
    fetch_ok=1; \
    if ! git fetch origin; then \
        fetch_ok=0; \
        echo "Warning: git fetch origin failed (offline?). Continue with local checks." >&2; \
    fi; \
    echo "==> quick status"; \
    git status --short; \
    if [[ -n "$(git status --porcelain)" ]]; then \
        echo "Working tree is not clean. Commit/stash changes before release." >&2; \
        exit 1; \
    fi; \
    if git rev-parse -q --verify "refs/tags/{{version}}" >/dev/null 2>&1; then \
        echo "Tag {{version}} already exists locally." >&2; \
        exit 1; \
    fi; \
    if [[ "$fetch_ok" -eq 1 ]]; then \
        if git ls-remote --exit-code --tags origin "refs/tags/{{version}}" >/dev/null 2>&1; then \
            echo "Tag {{version}} already exists on origin." >&2; \
            exit 1; \
        fi; \
    else \
        echo "Warning: skipped remote tag existence check (fetch failed)." >&2; \
    fi; \
    current_codex_version="$(python3 -c 'import json, pathlib; print(json.loads(pathlib.Path("plugins/python-structured-logging/.codex-plugin/plugin.json").read_text())["version"])')"; \
    current_claude_version="$(python3 -c 'import json, pathlib; print(json.loads(pathlib.Path("plugins/python-structured-logging/.claude-plugin/plugin.json").read_text())["version"])')"; \
    if [[ "$current_codex_version" != "$current_claude_version" ]]; then \
        echo "Plugin manifests are out of sync: codex=$current_codex_version claude=$current_claude_version" >&2; \
        exit 1; \
    fi; \
    if [[ "$current_codex_version" == "{{version}}" ]]; then \
        echo "Plugin manifests already have version {{version}}. Use a new version." >&2; \
        exit 1; \
    fi; \
    python3 scripts/check_release_state.py; \
    echo "==> preflight passed for {{version}}"

[group('Release')]
[doc('Update plugin manifest versions to a target version (x.y.z)')]
release-update version:
    python3 scripts/set_plugin_version.py "{{version}}"
    python3 scripts/check_release_state.py --expected-version "{{version}}"

[group('Release')]
[doc('Full release flow: preflight -> bump versions -> checks -> commit -> tag -> push')]
release version:
    @just release-preflight {{version}}; \
    echo "==> bump plugin versions to {{version}}"; \
    just release-update {{version}}; \
    echo "==> commit release changes"; \
    git add plugins/python-structured-logging/.codex-plugin/plugin.json plugins/python-structured-logging/.claude-plugin/plugin.json; \
    git commit -m "Release {{version}}"; \
    echo "==> create annotated tag {{version}}"; \
    git tag -a "{{version}}" -m "Release {{version}}"; \
    echo "==> push commit + tag to origin"; \
    git push origin HEAD; \
    git push origin "refs/tags/{{version}}"; \
    echo "==> done. GitHub Actions release workflow should start for tag {{version}}."
