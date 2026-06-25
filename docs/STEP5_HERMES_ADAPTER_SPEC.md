# STEP 5 Hermes Research Adapter Specification

## Purpose

STEP 5 connects the deterministic STEP 4 orchestrator to real Hermes-managed research/search tools. The repository must remain credential-free. Actual Hermes tool calls are performed outside this repo and injected through the ResearchAdapter contract.

## Boundary

- Repo owns: query plan schema, raw result schema, validation, normalization, analysis, report generation.
- Hermes/Sake layer owns: actual web/search/API/tool execution, credentials, rate limits, and source access.

## Input Contract

ResearchAdapter receives:

```json
{
  "period_id": "YYYY-MM",
  "week_id": "legacy-compatible-id",
  "queries": [
    {
      "query_id": "string",
      "compressor_type": "Re|Ro|Sc",
      "competitor": "normalized competitor",
      "category": "canonical category",
      "refrigerants": ["R290"],
      "keywords": ["query string"],
      "priority": "primary|secondary|primary-replan"
    }
  ],
  "source_priority": {}
}
```

## Output Contract

ResearchAdapter must return:

```json
{
  "period_id": "YYYY-MM",
  "week_id": "legacy-compatible-id",
  "results": [
    {
      "query_id": "string",
      "source_url": "https://...",
      "source_date": "YYYY-MM-DD",
      "source_type": "official|exhibition|patent|academic|trade_media|news",
      "title": "string",
      "summary": "string",
      "raw_text": "short excerpt or summary only",
      "competitor": "string",
      "compressor_type": "Re|Ro|Sc",
      "category": "canonical category",
      "refrigerants": ["R290"],
      "samsung_status": "보유|미보유|대응중|확인필요"
    }
  ]
}
```

## Source and Safety Rules

- Use `config/source_whitelist.yaml`.
- Respect robots.txt.
- No broad crawling.
- No sitemap traversal.
- Academic sources: title + abstract only.
- Do not store credentials, API keys, cookies, OAuth tokens, private PDFs, or internal Samsung data in repo outputs.

## Error Semantics

- Return partial results when possible.
- Include no fabricated results.
- If source access fails, return an empty result list for that query and let STEP 4 fallback/human review gate handle it.

## STEP 5 Acceptance

```bash
uv run python -m comp_research_mas.cli run-monthly --manual --period-id YYYY-MM
uv run --extra test pytest -q
```
