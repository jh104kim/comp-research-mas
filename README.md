# 압축기 경쟁사 모니터링 MAS

C&M 압축기 경쟁사/냉매/규제/특허 동향을 월간으로 수집하고, 삼성 관점 Gap Matrix와 HTML KPI Dashboard를 생성하는 다중 에이전트 시스템입니다.

## 목적

- 2025-07~2026-06 기간의 Re/Ro/Sc 압축기 경쟁 동향 누적 분석
- R290, R600a, R32, R454B/R454C 등 냉매 전환 신호 추적
- GMCC/Midea, LG, Copeland/Emerson, Embraco/Nidec, Secop, Danfoss 등 경쟁사 커버리지 확보
- 공식/전시/특허/규제/업계 미디어 기반 evidence ledger 유지
- Writer/Critic/Guardian gate로 보고서 품질과 보안 검증

## Phase A~I 아키텍처

- Phase A: stub URL placeholder, dynamic evidence threshold, critic rubric 강화
- Phase B/B-2: 2025-10 live pilot + targeted enrichment
- Phase C: 2025-07~2026-06 전체 backfill live-shaped 실행
- Phase D: Chroma-compatible local VectorStore + FileVectorStore fallback
- Phase E: Critic↔Writer DebateRound schema와 HTML 표시
- Phase F: high threat alert dry-run payload
- Phase G: yaml 기반 orchestration config
- Phase H: Stub/Claude/Codex LLMAdapter dry-run 구조
- Phase I: PDF/OCR multimodal EvidenceItem 확장

## 에이전트 구성

1. Query Planner: period/source/query plan 생성
2. Research Adapter: whitelist source title+summary raw JSON 수집/주입
3. Evidence Normalizer: canonical status, refrigerant, trust_score 정규화
4. Analyst: Gap Matrix, high threat, new signal 생성
5. Writer: 월간 보고서 작성
6. Critic: 10점 rubric, debate_points, hard_fail 판단
7. Notifier/Live Sender: Gmail/Slack/Obsidian payload 및 live gate
8. Guardian: 비밀값/내부정보 패턴 scan

## 설치

```bash
uv sync --extra test
```

## 주요 CLI

```bash
# 2025-10 query plan 확인
uv run python -m comp_research_mas.cli run-backfill --from-period 2025-10 --to-period 2025-10 --dry-run --show-query-plan

# injected raw 결과로 backfill 실행
uv run python -m comp_research_mas.cli run-backfill --from-period 2025-10 --to-period 2025-10 --no-dry-run --injected-results-path outputs/search/2025-10_raw_results_merged.json

# 전체 테스트
uv run --extra test pytest -q

# Vector DB
uv run python -m comp_research_mas.cli rebuild-vector-store
uv run python -m comp_research_mas.cli vector-search "R290 GMCC" --top-k 3

# Alert / Config / LLM / Multimodal
uv run python -m comp_research_mas.cli alert-dry-run --period-id 2026-06
uv run python -m comp_research_mas.cli config-validate
uv run python -m comp_research_mas.cli llm-dry-run --provider claude
uv run python -m comp_research_mas.cli parse-sample-pdf --path tests/fixtures/sample_catalog.pdf

# Guardian
uv run python -m comp_research_mas.cli guardian-scan --path outputs/
```

## 설정 파일

- `config/source_whitelist.yaml`: 허용 소스와 trust_score
- `config/exhibition_calendar.yaml`: 전시회 월 source boost
- `config/alert_policy.yaml`: high/medium/low alert 정책
- `config/competitors.yaml`: primary/secondary 경쟁사
- `config/compressor_types.yaml`: Re/Ro/Sc와 냉매
- `config/agent_roles.yaml`: 에이전트 역할 정의
- `config/source_policy.yaml`: whitelist-only, title-summary-only 정책
- `config/rubric.yaml`: critic 10점 rubric

## 출력 구조

- `outputs/search/*.json`: raw search/injected results
- `outputs/evidence/*_evidence.json`: 정규화 evidence
- `outputs/analysis/*_analysis_bundle.json`: Gap Matrix/Signal
- `outputs/reviews/*_critic_review.json`: Critic rubric 결과
- `outputs/reports/*.md|*.html`: 월간/백필 리포트
- `outputs/memory/evidence_ledger.json`: 누적 evidence ledger
- `outputs/memory/gap_matrix_history.json`: 누적 Gap Matrix history
- `outputs/vector_store/chroma/index.json`: local vector index
- `outputs/outbox/*`: Gmail/Slack/Obsidian/alert payload
- `outputs/logs/*`: Guardian/alert/live sender 로그

## 환경변수

비밀값은 repo에 저장하지 않습니다. 필요한 키 이름만 사용합니다.

- `GMAIL_SENDER`
- `GMAIL_APP_PASSWORD`
- `SLACK_WEBHOOK_URL`
- `OBSIDIAN_VAULT_PATH`
- `COMP_RESEARCH_LLM_PROVIDER=stub|claude|codex`

## 제한사항

- broad crawling 금지
- whitelist source만 사용
- 제목+요약/초록 수준 수집 원칙
- 학술/특허/규제 전문 분석은 별도 단계 필요
- live LLM/Gmail/Slack은 approval/환경변수 gate를 통과해야 함
- 삼성 내부 스펙/미공개 로드맵/비밀값 저장 금지

## 현재 검증 상태

- Backfill period_count: 12
- Total evidence: 136
- Latest period: 2026-06
- Latest critic_score: 10
- Test: 63 passed
- Guardian outputs scan: pass
