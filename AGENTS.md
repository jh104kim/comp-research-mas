# AGENTS.md — comp-research-mas

## Project Rule

This repository implements the C&M compressor competitor monitoring MAS.

## Current STEP

- STEP 1: complete — LangGraph Writer + Critic self-refine loop.
- STEP 2: complete — Search Agent stub/query/evidence normalization.
- STEP 3: complete — Analyst Agent, Gap Matrix, AnalysisBundle, anomaly signals.
- STEP 3 Retrofit: complete — Planning/Memory/CoT/RAG retrofits with stricter threat thresholds.

## Safety Rules

- Do not store Samsung internal model names, internal specs, customer data, cost, roadmap, credentials, tokens, or API keys.
- Samsung comparison status must use only: `보유`, `미보유`, `대응중`, `확인필요`.
- Repo code must only include LLM/research adapter interfaces or stubs. Real Hermes/Codex/search calls stay outside this repo until STEP 5.
- No broad crawling. No sitemap traversal. Respect robots.txt. Use high-trust selected sources only.

## Output Rules

- Markdown report: executive 1–2 page summary orientation.
- JSON evidence appendix: detailed sources, trust scores, dynamic tags, threat levels.
- JSON analysis bundle: Gap Matrix, threat summary, and new signals.
- JSON memory outputs: `outputs/memory/evidence_ledger.json`, `outputs/memory/gap_matrix_history.json`.
- JSON critic CoT: `outputs/reviews/YYYY-MM-DD_critic_cot.json`.
- Outputs under `outputs/` are local artifacts and not committed.

## Documentation Rule

When changing schemas, agent flow, or step gates, update all relevant docs consistently:
- `README.md`
- `docs/PROJECT_PLAN.md`
- `docs/MAS_SPEC.md`
- `config/gap_matrix_baseline.yaml` when Gap Matrix baseline changes
- step-specific docs such as `docs/STEP2_SEARCH_AGENT_PLAN.md`
- this `AGENTS.md`
