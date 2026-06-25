# PROJECT PLAN

## 완료 범위

Phase A~I까지 C&M 압축기 경쟁사 모니터링 MAS를 확장했다.

## Phase별 산출

- A: Critic rubric, dynamic threshold, stub URL placeholder
- B/B-2: 2025-10 live pilot, Ro/특허/규격/성능 보강
- C: 2025-07~2026-06 전체 backfill, 총 evidence 136건
- D: Chroma-compatible VectorStore + File fallback
- E: DebateRound schema와 HTML Critic Review 표시
- F: high threat alert dry-run Slack payload
- G: yaml orchestration config + validation
- H: Stub/OpenAI/Codex LLMAdapter dry-run
- I: PDF/OCR multimodal EvidenceItem

## 운영 원칙

- whitelist source only
- title+summary only
- secrets never committed
- Guardian scan before force-adding outputs
- live send only behind environment/approval gate
