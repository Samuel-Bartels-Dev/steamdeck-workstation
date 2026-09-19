# ADR-005: JSON for Bootstrap-Critical Manifests

**Status:** Accepted

Use JSON for bootstrap-critical desired-state profiles and module manifests in v0.1.0. Python's standard library can parse it on a clean SteamOS environment, avoiding a `yq`/PyYAML dependency before the dependency manager itself is available. Human-facing design information remains Markdown.
