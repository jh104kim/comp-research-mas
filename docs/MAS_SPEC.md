# MAS 기획서 — C&M 압축기 경쟁사 모니터링

## 1. 시스템 개요

| 항목 | 내용 |
|---|---|
| 목적 | 압축기 경쟁사 신제품·스펙·특허·인증·냉매 전환·전시회 동향을 선별 수집하고 삼성 경쟁 관점으로 주간 리포트화 |
| 대상 타입 | Re, Reciprocating / Ro, Rotary / Sc, Scroll |
| 대상 냉매 | 타입별 고정 금지. 삼성 경쟁 라인업과 관련된 R290, R600a, R134a, R1234yf, R32, R454B, R454C, R410A, R466A 등 포괄 |
| 용도 범위 | Residential, Unitary, Heat pump. 상업용 제외 |
| 실행 주기 | STEP 4부터 매주 월요일 자동 트리거 |
| 출력 | Markdown 리포트, evidence JSON, critic review JSON, STEP 5부터 Obsidian 저장 + 이메일 발송 |
| 핵심 원칙 | 전체 크롤링 금지. 고신뢰·고멘션·고인용 소스만 선별. 모든 분석은 삼성 Gap/우위/열위 관점 포함. 삼성 비교는 `보유/미보유/대응 중/확인 필요` 추상 상태만 사용 |

## 1.1 확정 의사결정

- 삼성 비교 기준선: `보유 / 미보유 / 대응 중 / 확인 필요`만 사용한다.
- 내부 스펙·모델명 직접 기재는 금지한다.
- STEP 3 이후 별도 내부 매핑 레이어 추가를 검토한다.
- 리포트 본문은 임원용 1~2페이지 요약으로 제한한다.
- 상세 근거는 JSON evidence appendix로 분리 저장한다.
- repo 내부는 LLM adapter interface만 구현하고, 실제 키·토큰·LLM 호출은 Hermes/Codex 위임 레이어가 담당한다.

## 2. 에이전트 역할 정의

### Orchestrator

- LangGraph StateGraph로 전체 흐름 제어
- STEP별 활성 노드 관리
- Writer/Critic self-refine 반복 제어
- 실패 시 재시도·human review flag 결정
- 각 STEP 완료 후 다음 STEP 진행 여부를 사용자에게 확인

### Source Planner

- 이번 주 모니터링할 타입, 경쟁사, 냉매, 카테고리, 소스 후보를 만든다.
- 전체 크롤링 대신 source whitelist와 query registry를 사용한다.
- 고신뢰 소스 우선순위와 제외 기준을 기록한다.

### Search / Research Agent

- Hermes 내장 리서치 기능으로 제한 검색한다.
- 공식 웹사이트, 공식 전시회 보도자료, 특허/인증 DB, 업계 주요 매체를 우선 사용한다.
- 뉴스는 제목+요약 중심, 학술은 제목+초록만 사용한다.
- 무차별 크롤링, 전문 대량 수집, robots.txt 위반을 하지 않는다.

### Evidence Normalizer

- 수집 결과를 `EvidenceItem` schema로 변환한다.
- 필수 필드:
  - compressor_type: Re/Ro/Sc
  - competitor: 정규화된 이름
  - refrigerant: 복수 list
  - category: 8개 canonical 카테고리
  - samsung_status: 보유/미보유/대응중/확인필요
  - trust_score: 1~5
  - source_type: official/exhibition/patent/academic/trade_media/news
  - threat_level: high/medium/low/none
  - week_id, source_url, source_date, raw_text
- 확장 필드:
  - product_or_series
  - condition_or_capacity
  - application
  - source_name
  - is_primary
  - low_confidence
  - dynamic_tags
- 수집 데이터에 따라 `dynamic_tags`를 부여하고, 반복적으로 중요해지는 태그는 STEP 3에서 정식 필드로 승격 검토한다.

### Analyst Agent

- 단순 요약이 아니라 삼성 경쟁 라인업 관점으로 분석한다.
- `config/gap_matrix_baseline.yaml`을 읽고 EvidenceItem[]과 교차 분석한다.
- config 원본은 수정하지 않고 분석 결과는 `outputs/analysis/YYYY-WW_analysis_bundle.json`에 저장한다.
- Re: 냉매별 × MBP/LBP/HBP 경쟁사 보유 모델 vs 삼성 보유/미보유
- Ro: 냉매별 default 조건 및 기술 수준 비교
- Sc: 냉매별 Fixed/Variable/TwoStage 비교
- AnalysisBundle:
  - gap_matrix
  - threat_summary
  - new_signals
  - week_id
  - baseline_used
- 이상 신호를 감지한다:
  - primary_new_entry
  - multi_competitor_entry
  - spec_change
  - new_refrigerant

### Writer Agent

- 정해진 3계층 리포트 구조를 완전 준수한다.
- Re/Ro/Sc 각 타입마다 8개 카테고리를 모두 출력한다.
- 정보가 없으면 공란이 아니라 `해당 없음 — 이번 주 확인된 고신뢰 근거 없음`으로 쓴다.
- 각 항목마다 `내용 / 삼성 비교 관점 / 출처`를 포함한다.
- 삼성 Gap 종합 현황 표와 다음 주 모니터링 포인트를 작성한다.
- 본문은 1~2페이지 요약을 목표로 하고 상세 근거는 evidence JSON으로 넘긴다.

### Critic Agent

0~10점으로 평가한다.

| 평가 항목 | 점수 |
|---|---:|
| Re/Ro/Sc + 8개 카테고리 + 경쟁사별 구조 준수 | 2 |
| 삼성 비교 관점 모든 주요 항목 반영 | 2 |
| Gap Matrix 표 존재 및 정확성 | 2 |
| high threat 핵심 동향 반영 | 1 |
| 출처 명시 여부 | 1 |
| ★ 최우선 경쟁사 누락 없는지 | 2 |

- 7점 이상: 통과
- 7점 미만: Writer 재작성, 최대 2회
- hard fail: 출처 0개, 타입 전체 누락, 삼성 비교 관점 전체 누락, AnalysisBundle 있는데 Gap Matrix 표 누락, high threat 핵심 동향 미반영, 민감정보 의심, fabrication risk high

### Output Agent

- Markdown, evidence JSON, critic JSON 저장
- STEP 5부터 Obsidian 저장과 이메일 발송 담당
- Critic 7점 미만 또는 hard fail이면 자동 발송하지 않고 human review로 남김

### LLM Adapter

- STEP 1에서는 interface/stub만 구현한다.
- repo 내부에서 실제 Codex 키·토큰·LLM 호출을 수행하지 않는다.
- 실제 작성/추론 호출은 Hermes/Sake/Codex 위임 레이어가 담당한다.

## 3. 리포트 구조

```text
Level 1: 압축기 타입, Re / Ro / Sc
  Level 2: 분석 카테고리 8개
    Level 3: 경쟁사별 세부 내용 + 삼성 비교 관점
```

8개 카테고리:
1. 신냉매·냉매 전환
2. 성능·효율
3. 신제품·라인업
4. 신뢰성·내구성
5. 특허·기술
6. 규격·인증
7. 가격·유통
8. 전시회·발표

## 4. STEP별 구축

### STEP 1 — Writer + Critic Self-Refine Loop

- LangGraph 최소 graph: `load_raw_data → writer → critic → conditional_refine → save_output`
- 입력: 수동 raw_data
- 출력: `YYYY-MM-DD_compressor_weekly.md`, critic review JSON
- 완료 조건: Re/Ro/Sc + 8개 카테고리 + 경쟁사별 + 삼성 비교 관점 + Gap 표 정상 출력

### STEP 2 — Search Agent

- 타입 × 경쟁사 × 냉매 × 카테고리 query registry
- Hermes 내장 리서치로 제한 검색
- EvidenceItem으로 정규화

### STEP 3 — Analyst Agent

- 삼성 Gap Matrix 자동 산출
- AnalysisBundle 생성
- high threat / new_signals 감지
- Writer/Critic 분석 품질 gate 연결

### STEP 4 — Orchestrator + Scheduler

- 매주 월요일 자동 실행
- 실패 시 최대 3회 재시도
- 실행 로그 저장

### STEP 5 — Output 자동화

- Obsidian 저장
- 이메일 발송
- 자동 발송 gate 적용

## 5. 공식 구현 계획

상세 구현 순서와 애매한 질문은 `docs/PROJECT_PLAN.md`를 기준으로 한다.


## 6. Planning / Memory / CoT / RAG Retrofit

### Planning

- Query Planner는 최초 evidence_count가 임계값보다 작으면 primary query를 확장하고 1회 재실행한다.
- Analyst가 empty이면 evidence 기반 fallback을 명시한다.

### Memory

- Evidence Ledger: `outputs/memory/evidence_ledger.json`
- Gap Matrix History: `outputs/memory/gap_matrix_history.json`
- 모든 memory 산출물은 로컬 outputs에만 저장하고 commit하지 않는다.

### CoT / Reasoning Log

- `WorkflowState.reasoning_log`에 노드별 판단 근거를 저장한다.
- Critic CoT는 `outputs/reviews/YYYY-MM-DD_critic_cot.json`에 저장한다.

### RAG

- Writer는 Evidence Ledger에서 타입+경쟁사+카테고리 기준 관련 evidence를 검색한다.
- 리포트에는 참조 evidence_ids를 명시한다.

### Threat 기준

- 미보유 + trust_score=5: high
- 미보유 + trust_score=4: medium
- 미보유 + trust_score=3: medium + low_confidence
- 대응중 + trust_score>=4: medium
- 대응중 + trust_score=3: low
- 보유: low
- 확인필요: none
- 이상 신호는 기본 trust_score=5만 허용한다. 단, primary_new_entry는 trust_score>=4부터 허용한다.


## 7. STEP 4 Monthly Orchestrator

- Monthly period is `period_id=YYYY-MM`.
- `week_id` remains for backward compatibility.
- Scheduler runs on the first Monday of each month and supports manual triggers.
- Orchestrator controls retry, fallback, human review gate, and alert.
- Human Review Gate triggers when:
  - critic score < 7
  - hard_fail = true
  - sensitive pattern detected
- Fallback policy:
  - Source Planner failure: previous period evidence fallback
  - Analyst failure: baseline gap matrix fallback
  - Writer failure: human review
  - Critic hard fail: auto publish blocked + alert
- Agent reasoning log includes:
  - node
  - step
  - judgment
  - reasoning
  - tool_used
  - rag_used
  - conclusion
- Real Hermes search is deferred to STEP 5.
