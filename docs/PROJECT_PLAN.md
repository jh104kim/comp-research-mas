# C&M 압축기 경쟁사 모니터링 MAS — 신규 구축 계획

> **For Hermes/Sake:** 이 계획은 구현 지시서다. 단계별로만 진행한다. 각 STEP 완료 후 실행 결과를 보고하고, 다음 STEP 진행 여부를 삿뽀로에게 확인한다.

**Goal:** 압축기 경쟁사 동향을 자동 수집·분석·리포트화하는 Multi-Agent System(MAS)을 구축한다.

**Architecture:** LangGraph `StateGraph` 기반으로 `Source Planning → Search/Research → Evidence Normalization → Analyst → Writer → Critic → Output` 흐름을 만든다. STEP 1은 자동 리서치 없이 수동 raw_data를 받아 Writer + Critic self-refine loop를 완성한다.

**Tech Stack:** Python 3.12, uv, LangGraph, Codex 연결 API abstraction, Hermes 내장 리서치, Markdown/JSON output, Obsidian, 향후 SMTP/email.

---

## 0. 현재 프로젝트 상태

- WSL: `/mnt/f/ai-app-dev/10-comp-research-mas`
- Windows: `F:\ai-app-dev\10-comp-research-mas`
- GitHub: `https://github.com/jh104kim/comp-research-mas`
- 현재 구현: 초기 Phase 1 MVP, 단순 Writer + Critic loop
- 신규 변경 방향: Re/Ro/Sc × 8개 카테고리 × 경쟁사별 삼성 비교 관점 구조로 재설계

## 1. 최상위 MAS 구성

### 1.1 에이전트 역할

| Agent | 목적 | 입력 | 출력 | 구현 시점 |
|---|---|---|---|---|
| Orchestrator | 전체 그래프 제어, 재시도, 중단, human review 판단 | WorkflowState | 다음 node routing | STEP 4, 단 STEP 1에서 최소 graph 구조 선반영 |
| Source Planner | 이번 주 볼 소스와 query 계획 생성 | monitor registry, 지난 리포트 | source plan | STEP 2 |
| Search/Research Agent | Hermes 내장 리서치로 선별 수집 | source plan | raw evidence | STEP 2 |
| Evidence Normalizer | 수집 결과를 표준 schema로 변환 | raw evidence | EvidenceItem[] | STEP 2 |
| Analyst Agent | 삼성 Gap/성능/냉매/타입 관점 분석 | EvidenceItem[] | AnalysisBundle | STEP 3 |
| Writer Agent | 3계층 리포트 작성 | raw_data 또는 AnalysisBundle | draft markdown | STEP 1 |
| Critic Agent | 구조/근거/삼성 관점/누락 평가 | draft, raw_data | score, feedback | STEP 1 |
| Output Agent | Markdown/JSON/Obsidian/email 저장 | approved report | files/delivery status | STEP 5 |

### 1.2 LangGraph 굵은 흐름

```text
START
  → source_planner          # STEP 2부터 활성
  → search_research         # STEP 2부터 활성
  → evidence_normalizer     # STEP 2부터 활성
  → analyst                 # STEP 3부터 활성
  → writer                  # STEP 1부터 활성
  → critic                  # STEP 1부터 활성
  → conditional:
       score >= 7            → output
       score < 7 and iteration < 2 → writer_rewrite
       score < 7 and iteration >= 2 → output_human_review_flag
  → END
```

STEP 1에서는 `load_raw_data → writer → critic → conditional_refine → save_output`만 구현한다.

## 2. 모니터링 관점 원칙

1. 삼성(당사) 압축기 라인업과 직·간접 경쟁 관계에 있는 냉매·타입·용도를 포괄 추적한다.
2. 냉매를 특정 타입에 고정하지 않는다.
3. 분석 기준은 항상 삼성 Gap, 삼성 대비 성능·스펙 우위/열위, 삼성 대응 필요성이다.
4. 상업용은 제외하고, 가정용 Residential / Unitary / Heat pump 중심으로 제한한다.
5. 출처 없는 주장은 리포트 본문에 단정형으로 넣지 않는다.

## 3. 모니터링 대상

### 3.1 Re, Reciprocating

경쟁사/시리즈:
- Embraco/Nidec: EM, NEK, NT, NE, FFI — R290, R600a, R134a 전반
- Secop: KL, NL, DL, SC, TL — MBP/LBP/HBP 조건 전반
- GMCC/Midea: PA, KA, QA — R290, R600a 병행
- LG: CMA — 공개 라인업 제한적, 동향 중심
- Panasonic: E-Series Inverter — COP·효율 데이터 검증 중심

삼성 경쟁 관점:
- 삼성 미보유 냉매 구간 경쟁사 모델
- COP·냉동능력 우위 모델
- MBP/LBP/HBP 조건별 경쟁 현황
- 삼성 진입 예정 구간의 경쟁사 선점 현황

### 3.2 Ro, Rotary

경쟁사/시리즈:
- Highly: R290, R32 Rotary 중심, 별도 관리
- LG: Rotary R290/R32
- GMCC/Midea: Rotary 일부 라인
- Panasonic: Rotary inverter

삼성 경쟁 관점:
- 삼성 Rotary 대비 냉매별 효율 격차
- 인버터 Rotary 기술 수준
- R290 Rotary 시장 진입 현황

### 3.3 Sc, Scroll

경쟁사/시리즈:
- GMCC/Midea: Fixed, Variable, Two-Stage — R454B, R32, R410A
- Danfoss: DSH — R454B, R410A
- LG: YPH/YBH, APH/ABH — R454B, R410A, R32
- Copeland/Emerson: YHV, ZO, ZOD — 냉매 전환 전 구간

삼성 경쟁 관점:
- 냉매별·용량별 성능 비교
- Variable/Two-Stage 기술 격차
- 신규 냉매 채택 현황
- 조건 정규화 기준 COP/냉동능력 비교

## 4. 리포트 고정 구조

리포트는 반드시 아래 3계층을 따른다.

```text
Level 1: 압축기 타입, Re / Ro / Sc
  Level 2: 분석 카테고리 8개
    Level 3: 경쟁사별 세부 내용 + 삼성 비교 관점
```

### 4.1 Level 2 공통 카테고리 8개

| 카테고리 | 수집 내용 | 삼성 비교 관점 |
|---|---|---|
| 신냉매·냉매 전환 | 신냉매 채택, A2L/A3 전환, 규제 대응 | 삼성 미대응 냉매 경쟁사 선점 여부 |
| 성능·효율 | COP, EER, 냉동능력, 인버터 효율 | 삼성 동급 모델 대비 우위/열위 |
| 신제품·라인업 | 신모델 출시, 시리즈 확장, 단종 | 삼성 Gap 구간 경쟁사 진입 여부 |
| 신뢰성·내구성 | 수명 데이터, 인증, 필드 이슈 | 삼성 대비 인증 범위 차이 |
| 특허·기술 | 신규 특허, 논문, R&D 방향 | 삼성 기술 방향과 충돌·위협 여부 |
| 규격·인증 | UL, CE, ENERGY STAR, 규제 | 삼성 미취득 인증 경쟁사 보유 여부 |
| 가격·유통 | 가격 변동, 공급망, OEM 계약 | 삼성 가격 경쟁력 위협 여부 |
| 전시회·발표 | AHR, Chillventa, China Ref Expo | 경쟁사 전략 방향 시그널 |

정보가 없는 카테고리도 공란으로 두지 않고 `해당 없음 — 이번 주 확인된 고신뢰 근거 없음`으로 명시한다.

## 5. 우선 모니터링 소스와 제한

### 5.1 우선 소스

1순위, 자연냉매/Re/Ro:
- Chillventa 공식 보도자료
- NaturalRefrigerants.com
- Cooling Post
- Hydrocarbons21

2순위, R454B/A2L/북미/Sc:
- AHR Expo 공식 발표
- ACHR News
- ASHRAE Journal 주요 논문

3순위, 아시아/중국계:
- JARN
- China Refrigeration Expo 보도자료

학술:
- International Journal of Refrigeration
- Applied Thermal Engineering
- 제목+초록만 사용, 전문 크롤링 금지

### 5.2 제한할 것

- 전체 크롤링 금지: sitemap 전체 순회, 대량 scraping 금지
- robots.txt 위반 금지
- 저신뢰 단일 블로그/리셀러 글을 단정 근거로 사용 금지
- 출처 없는 성능/가격/인증 주장 금지
- 삼성 내부 스펙, 미공개 로드맵, 고객/원가 정보 저장 금지
- Critic 7점 미만 또는 출처 부족 리포트 자동 발송 금지
- 냉매를 R290/R454B로만 고정 금지
- Re/Ro/Sc 중 특정 타입만 반복 분석 금지

## 6. STEP 1 상세 계획 — Writer + Critic Self-Refine Loop

### 6.1 목표

수동 입력 raw_data를 받아 고정 리포트 구조로 작성하고, Critic이 품질을 평가해 7점 미만이면 최대 2회 재작성한다.

### 6.2 State 구조

```python
class WorkflowState(TypedDict):
    raw_data: str | list[EvidenceItem]
    draft: str
    feedback: str | dict
    score: int
    iteration: int
    status: str
```

### 6.3 Writer Agent 요구사항

Writer는 반드시 다음을 만족해야 한다.

- Re / Ro / Sc 섹션 구분
- 각 타입마다 8개 카테고리 출력
- 카테고리 내 경쟁사별 구분
- 각 항목에 `삼성 비교 관점` 명시
- 정보 없는 카테고리는 `해당 없음` 명시
- `삼성 Gap 종합 현황` 표 생성
- `출처 목록` 섹션 생성

### 6.4 Critic Agent 10점 기준

| 평가 항목 | 점수 |
|---|---:|
| Re/Ro/Sc + 8개 카테고리 + 경쟁사별 구조 준수 | 2 |
| 삼성 비교 관점 모든 주요 항목 반영 | 3 |
| 삼성 Gap 표 정확성/구조 | 2 |
| 출처 명시 여부 | 1 |
| 경쟁사 누락 없는지 | 1 |
| 분량·가독성 | 1 |

- 7점 이상: 통과
- 7점 미만: Writer 재실행
- 최대 2회 반복 후 강제 종료, human review flag 저장

### 6.5 STEP 1 구현 파일

- Modify: `src/comp_research_mas/models.py`
- Create/Modify: `src/comp_research_mas/agents.py`
- Create: `src/comp_research_mas/graph.py`
- Create/Modify: `src/comp_research_mas/tools.py`
- Create/Modify: `src/comp_research_mas/output.py`
- Create/Modify: `src/comp_research_mas/config.py`
- Modify: `src/comp_research_mas/cli.py`
- Replace sample: `examples/manual_search_results/step1_raw_data.md`
- Modify tests: `tests/test_step1_langgraph.py`

### 6.6 STEP 1 완료 조건

다음 명령이 통과해야 한다.

```bash
uv run python -m comp_research_mas.cli run-step1-sample
uv run --extra test pytest -q
```

산출물:
- `outputs/reports/YYYY-MM-DD_compressor_weekly.md`
- `outputs/reviews/YYYY-MM-DD_critic_review.json`
- `outputs/evidence/YYYY-MM-DD_evidence.json` 또는 raw snapshot

리포트에는 반드시 포함:
- Re/Ro/Sc
- 8개 카테고리
- 경쟁사별 세부 내용
- 삼성 비교 관점
- 삼성 Gap 종합 현황 표
- 출처 목록

## 7. 단계별 구축 게이트

### STEP 1 완료 후 확인 필요

삿뽀로 확인 없이 STEP 2 자동 검색 구현으로 넘어가지 않는다.

보고할 것:
- 생성된 Markdown 경로
- Critic 점수
- 재작성 횟수
- 구조 누락 여부
- 테스트 결과
- 다음 단계 제안

### STEP 2 — Search Agent

목표:
- 타입 × 경쟁사 × 냉매 × 카테고리 query registry 구성
- Hermes 내장 리서치로 제한 검색
- 결과를 Re/Ro/Sc × 8개 카테고리 × 경쟁사로 분류

완료 조건:
- Search → 자동 분류 → Writer 전달 흐름 동작
- 전체 크롤링 없이 source log 저장

### STEP 3 — Analyst Agent

목표:
- Re: 냉매별 × MBP/LBP/HBP 경쟁사 보유 vs 삼성 보유/미보유
- Ro: 냉매별 × inverter/fixed 커버리지 비교
- Sc: 냉매별 × 용량 구간별 조건 정규화 비교
- 이상 신호: 급격한 스펙 변경, 삼성 Gap 신규 진입, 미보유 냉매 선점

완료 조건:
- 분석 결과가 구조화되어 Writer에 전달됨

### STEP 4 — Orchestrator + Scheduler

목표:
- 매주 월요일 자동 실행
- 실패 시 최대 3회 재시도
- 실행 로그 저장

완료 조건:
- 전체 파이프라인 자동 실행

### STEP 5 — Output 자동화

목표:
- Obsidian 저장
- 이메일 발송

Obsidian 후보:
- `/mnt/f/ai-obsidian/지식창고/raw/inbox/comp-research/YYYY-MM-DD_compressor_weekly.md`

이메일 제목:
- `[주간] 압축기 경쟁사 모니터링 YYYY-MM-DD`

완료 조건:
- Obsidian 저장 + 이메일 발송 자동 동작

## 8. 추가 아이디어

### 8.1 Source Trust Score

Evidence마다 신뢰도 점수를 둔다.

| 출처 유형 | 기본 점수 |
|---|---:|
| 경쟁사 공식 제품 페이지/카탈로그 | 5 |
| 공식 전시회/보도자료 | 5 |
| 특허/인증 DB | 5 |
| 학술 제목+초록 | 4 |
| 전문 업계 매체 | 3 |
| 일반 뉴스/블로그 | 1~2 |

Critic은 3점 미만 근거를 단정 표현에 쓰지 못하게 한다.

### 8.2 Evidence Ledger

리포트와 별도로 JSON evidence ledger를 저장한다.

목적:
- 추후 Analyst Agent가 과거 리포트와 변화점 비교
- 출처 감사 가능
- Obsidian에는 요약, repo에는 sanitized evidence만 유지

### 8.3 Hard Fail 조건

점수와 무관하게 즉시 human review로 보내는 조건:
- 출처 목록 0개
- Re/Ro/Sc 중 전체 타입 누락
- 삼성 비교 관점 전체 누락
- 민감정보 의심 문자열 발견
- Critic이 `fabrication_risk: high`로 판단

### 8.4 Human Approval Gate

STEP 5 이메일 발송 전에는 아래 조건을 만족해야 한다.
- Critic 7점 이상
- hard fail 없음
- 출처 3개 이상 또는 “이번 주 신규 고신뢰 근거 없음” 명시
- 민감정보 검사 통과

## 9. 애매해서 확인 필요한 질문

1. 삼성 비교 기준의 기준선은 무엇인가?
   - 내부 모델명/스펙을 쓰면 민감할 수 있으므로, 우선은 `삼성 보유/미보유/대응 중/확인 필요` 같은 추상 상태로 둘까요?
2. 리포트 깊이는 어느 쪽이 맞습니까?
   - A안: 임원용 1~2페이지 요약
   - B안: 실무자용 상세 evidence appendix 포함
3. 가격·유통 정보는 포함해도 됩니까?
   - 공개 리셀러 가격도 노이즈/민감도 리스크가 있습니다.
4. 특허·인증 지역 우선순위는 어떻게 둘까요?
   - US/EU/CN/KR/JP 중 필수 범위를 정해야 합니다.
5. 이메일 자동 발송 수신자는 누구로 할까요?
   - 초기에는 Obsidian 저장까지만 하고 이메일은 승인 후 진행을 권장합니다.
6. Codex 연결 API의 실제 호출 방식은 이 repo 내부에서 구현할까요, 아니면 Hermes가 실행 시 Codex/Coding agent로 위임하는 방식으로 둘까요?

## 10. 바로 다음 작업

다음 구현 작업은 STEP 1 재구현이다.

우선순위:
1. `models.py`에 EvidenceItem / WorkflowState schema 추가
2. `writer.py`를 Re/Ro/Sc × 8개 카테고리 고정 출력으로 교체
3. `critic.py`를 10점 rubric + hard fail로 교체
4. `graph.py`에 LangGraph self-refine loop 구현
5. `cli.py`에 `run-step1-sample` 추가
6. sample raw_data 교체
7. pytest로 구조와 refine 조건 검증
