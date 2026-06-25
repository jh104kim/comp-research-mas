# AGENTS

This repo implements a gated compressor competitor monitoring MAS.

## Required Practices

- Run `uv run --extra test pytest -q` before committing.
- Run `uv run python -m comp_research_mas.cli guardian-scan --path outputs/` before force-adding outputs.
- Do not commit secrets, tokens, Samsung internal specs, or unpublished roadmaps.
- Keep live search results in `outputs/search/` and inject via CLI.
- Prefer deterministic stubs/fallbacks for tests.

## Key Commands

- `run-backfill`
- `rebuild-vector-store`
- `vector-search`
- `alert-dry-run`
- `config-validate`
- `llm-dry-run`
- `parse-sample-pdf`
- `guardian-scan`
