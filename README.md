# C&M 압축기 경쟁사 모니터링 MAS

C&M 압축기 경쟁사 모니터링 Multi-Agent System(MAS) 프로젝트입니다.

## 목표

- 경쟁사 신제품, 스펙, 특허, 인증, 냉매 전환, 전시회 동향을 주간 단위로 선별 수집
- Re(Reciprocating) / Ro(Rotary) / Sc(Scroll) 전 타입을 포괄
- 냉매를 특정 타입에 고정하지 않고 삼성 경쟁 라인업 관점으로 추적
- Samsung Gap, 삼성 대비 성능·스펙 우위/열위, 대응 필요성을 중심으로 분석
- 주간 리포트를 Markdown/JSON으로 생성하고, 향후 Obsidian/email로 자동 전달

## 현재 구현 단계

- STEP 1 구현 완료
  - LangGraph 기반 Writer + Critic self-refine loop
  - Re/Ro/Sc × 8개 카테고리 × 경쟁사별 삼성 비교 관점 고정 출력
  - Critic 0~10점, 7점 미만 최대 2회 재작성
  - ★ 최우선 경쟁사 누락 감점/hard fail 검증
- STEP 2 구현 완료
  - Query planner
  - Research adapter stub
  - Evidence normalizer
  - Dynamic tags
  - ReportMetadata
  - STEP 1 Writer/Critic 자동 연결
- STEP 3 구현 완료
  - Analyst Agent 추가
  - `config/gap_matrix_baseline.yaml` 기준선 기반 Gap Matrix 산출
  - AnalysisBundle 생성
  - high threat / new_signals 감지
  - Writer AnalysisBundle 우선 작성
  - Critic 분석 품질 평가 및 hard fail 추가

- STEP 3 Retrofit 완료
  - Planning: evidence_count 기준 동적 재계획/re-run
  - Memory: evidence ledger와 gap matrix history 누적 저장
  - CoT: reasoning_log와 critic_cot 저장
  - RAG: Evidence Ledger 기반 관련 근거 참조 및 evidence_ids 표시
  - Threat 기준 상향 조정으로 과탐지 완화
- 다음 작업: STEP 4 Orchestrator 구조 정비, STEP 5 실제 Hermes Research Adapter 연결
  - Planning/Memory/CoT/RAG 구조 유지
  - 스케줄러/재시도/로그 관리
  - human review gate 유지
  - 실제 Hermes 검색 연결은 STEP 5에서 수행

## 확정 의사결정

- 삼성 비교 기준선은 `보유 / 미보유 / 대응 중 / 확인 필요`만 사용합니다.
- 내부 스펙·모델명 직접 기재는 금지합니다.
- 본문 리포트는 임원용 1~2페이지 요약으로 제한합니다.
- 상세 근거는 JSON evidence appendix로 분리 저장합니다.
- repo 내부는 LLM adapter interface만 구현하고 실제 Codex/Hermes 호출은 repo 밖 위임 레이어가 담당합니다.

## 빠른 실행, 현재 MVP

```bash
cd /mnt/f/ai-app-dev/10-comp-research-mas
uv run python -m comp_research_mas.cli run-sample
uv run --extra test pytest -q
```

결과:
- `outputs/reports/sample-weekly-report.md`
- `outputs/reports/sample-critic-review.json`

## 경로

Windows:

```text
F:\ai-app-dev\10-comp-research-mas
```

WSL:

```text
/mnt/f/ai-app-dev/10-comp-research-mas
```

## 주요 문서

- `docs/PROJECT_PLAN.md` - 신규 공식 구축 계획, MAS/Agentic workflow/STEP별 gate
- `docs/MAS_SPEC.md` - 에이전트 역할과 리포트 구조 정의
- `docs/PROJECT_PLAN_REDEFINED.md` - 메타 프롬프트 반영 설계 초안
- `docs/PHASE1_MVP.md` - STEP 1 Writer+Critic self-refine 구현 기준
- `docs/STEP2_SEARCH_AGENT_PLAN.md` - STEP 2 Search Agent 구현 기준과 완료 결과
- `config/gap_matrix_baseline.yaml` - STEP 3 Gap Matrix 기준선
- `AGENTS.md` - repo 내 에이전트 작업 규칙

## STEP Gate 원칙

각 STEP 완료 후 다음을 보고하고, 삿뽀로 확인 후 다음 STEP으로 넘어갑니다.

- 실행 명령
- 생성 파일
- Critic 점수
- 테스트 결과
- 누락/제한/리스크
- 다음 STEP 진행 여부 확인
