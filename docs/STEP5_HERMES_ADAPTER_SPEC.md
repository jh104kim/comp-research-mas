# STEP5 HERMES ADAPTER SPEC

## External Search Injection Pattern

Hermes performs source-limited research outside the repo, writes validated JSON to `outputs/search/{period}_raw_results*.json`, then injects it with:

```bash
uv run python -m comp_research_mas.cli run-backfill --from-period YYYY-MM --to-period YYYY-MM --no-dry-run --injected-results-path outputs/search/YYYY-MM_raw_results_live.json
```

## Security Boundary

- no provider keys in repo
- whitelist source URLs only
- title/summary/excerpt collection only
- Guardian scan before committing outputs

## Live Delivery

`live_sender.py` supports Gmail SMTP via `GMAIL_APP_PASSWORD`, Slack webhook via `SLACK_WEBHOOK_URL`, and Obsidian write via `OBSIDIAN_VAULT_PATH`.
