# C&M 압축기 경쟁사 모니터링 MAS Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** C&M 압축기 경쟁사 동향을 주간 단위로 수집·분석·작성·검증·저장하는 MAS를 단계적으로 구현한다.

**Architecture:** Phase 1은 외부 API 없이 Writer + Critic self-refine 루프를 구현한다. Phase 2부터 Search Agent, Phase 3부터 Analyst Agent, Phase 4부터 LangGraph Orchestrator, Phase 5부터 이메일/Obsidian 출력을 연결한다.

**Tech Stack:** Python 3.12, uv, Markdown, pytest, 향후 LangGraph/Claude Sonnet/Web Search/Google Patents API/Obsidian.

---

## 현재 상태

- 폴더: `/mnt/f/ai-app-dev/10-comp-research-mas`
- Windows: `F:i-app-dev-comp-research-mas`
- 초기 repo는 비어 있었음.
- 본 계획과 Phase 1 MVP 스캐폴드를 먼저 생성한다.

## 핵심 설계 원칙

1. 회사 내부 민감정보는 입력/출력에 원문 저장하지 않는다.
2. Search 결과에는 출처 URL과 날짜를 필수로 둔다.
3. 리포트는 Samsung Gap 관점을 별도 섹션으로 둔다.
4. Critic은 Writer 품질을 독립 평가하고 최대 2회 refine한다.
5. 자동화는 M1 수동 입력 → M2 주간 cron → M3 이벤트 기반 순서로 올린다.
6. Sake는 오케스트레이터로 남고, Search/Analyst/Writer/Critic은 별도 역할로 분리한다.

## Phase 1 — Writer + Critic MVP

목표:
- 수동 검색 결과 Markdown을 입력한다.
- Writer가 주간 리포트 초안을 만든다.
- Critic이 출처, 누락 경쟁사, Samsung Gap, 가독성 기준으로 평가한다.
- 기준 미달이면 Writer가 최대 2회 보완한다.

완료 기준:
- 샘플 입력으로 Markdown 리포트 생성
- Critic JSON 생성
- pytest 통과

파일:
- `src/comp_research_mas/models.py`
- `src/comp_research_mas/writer.py`
- `src/comp_research_mas/critic.py`
- `src/comp_research_mas/pipeline.py`
- `src/comp_research_mas/cli.py`
- `examples/manual_search_results/sample_2026w26.md`
- `tests/test_phase1.py`

검증:
```bash
uv run python -m comp_research_mas.cli run-sample
uv run pytest -q
```

## Phase 2 — Search Agent

목표:
- 경쟁사/제품/냉매별 검색 query registry를 만든다.
- 공식 사이트, Google Patents, 뉴스 검색 결과를 표준 schema로 저장한다.

주요 산출물:
- `config/monitors.yaml`
- `src/comp_research_mas/search_agent.py`
- `data/raw/YYYY-WW/*.json`

## Phase 3 — Analyst Agent

목표:
- R290 Re와 R454B Sc 기준으로 조건 정규화와 Gap Matrix 비교를 수행한다.
- 신규 특허/논문/스펙 변화의 이상 신호를 탐지한다.

주요 산출물:
- `src/comp_research_mas/analyst.py`
- `data/reference/samsung_gap_matrix.yaml`
- `outputs/analysis/YYYY-WW.json`

## Phase 4 — LangGraph Orchestrator + Scheduler

목표:
- StateGraph로 Search → Analyst → Writer → Critic → refine 조건부 흐름을 구현한다.
- 월요일 주간 실행 스케줄을 연결한다.

LangGraph 설계:
```text
START
  → search
  → analyst
  → writer
  → critic
  → conditional: pass → output / revise → writer / fail → human_review
  → END
```

## Phase 5 — Output 자동화

목표:
- Markdown 리포트를 Obsidian에 저장한다.
- 이메일 발송을 연결한다.
- 실패 시 Slack 또는 CLI로 짧게 보고한다.

저장 후보:
- Obsidian: `/mnt/f/ai-obsidian/지식창고/raw/inbox/comp-research/YYYYMMDD-weekly-competitor-report.md`
- 프로젝트 출력: `outputs/reports/YYYY-WW-weekly-report.md`

## 다음 실행 순서

1. Phase 1 MVP 실행 확인
2. 샘플 입력을 실제 수동 조사 결과로 교체
3. Critic 기준을 삿뽀로 업무 기준에 맞게 보정
4. Search Agent query registry 작성
5. LangGraph Orchestrator로 전환
