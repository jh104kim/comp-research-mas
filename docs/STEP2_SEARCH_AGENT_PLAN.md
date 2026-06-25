# STEP 2 계획 — Search Agent 추가

## 목표

STEP 1에서 완성한 `Writer + Critic self-refine` 루프의 입력을 수동 raw_data에서 자동 선별 evidence bundle로 전환한다.

핵심은 전체 크롤링이 아니라, 타입 × 경쟁사 × 냉매 × 카테고리 조합별로 고신뢰 소스만 제한 검색하고 `EvidenceItem` schema로 정규화하는 것이다.

## 전제

- STEP 1 E2E 통과 후에만 진행한다.
- repo 내부에는 실제 LLM/Codex 키를 넣지 않는다.
- Hermes 내장 리서치 또는 외부 위임 레이어가 실제 검색을 수행한다.
- Search Agent는 우선 query plan과 normalization을 구현하고, 실제 웹 검색은 adapter/stub 경계 뒤에 둔다.

## 입력

- `config/monitors.yaml`
- `src/comp_research_mas/models.py`의 우선 경쟁사 정의
- 소스 whitelist
- 주차/날짜

## Search Agent 구성

### 1. Source Planner

역할:
- 이번 주 검색할 query plan 생성
- Re/Ro/Sc별 ★ 최우선 경쟁사 우선
- 8개 카테고리별 query 생성
- 소스 우선순위 부여

출력 예시:

```json
{
  "week": "2026-W26",
  "queries": [
    {
      "compressor_type": "Re",
      "competitor": "GMCC/Midea",
      "category": "신제품·라인업",
      "query": "GMCC Midea PA KA QA R290 reciprocating compressor new model 2026",
      "source_priority": ["official", "exhibition", "industry_news"]
    }
  ]
}
```

### 2. Research Adapter

역할:
- STEP 2에서는 interface/stub 우선 구현
- 실제 Hermes 리서치 호출은 Sake/Hermes 실행 레이어가 담당
- 결과는 raw result list로 받는다.

금지:
- 사이트 전체 크롤링
- sitemap 순회
- robots.txt 위반
- 전문 논문/전문 기사 대량 수집

### 3. Evidence Normalizer

역할:
- raw result를 `EvidenceItem`으로 변환
- Re/Ro/Sc, 8개 카테고리, 경쟁사, 냉매, source, trust_score 태깅
- 중복 제거
- trust_score 3 미만은 단정 표현 금지 후보로 표시

## 우선 query 범위

### Re 최우선

- GMCC/Midea PA KA QA R290 R600a reciprocating compressor
- LG CMA R290 reciprocating compressor

### Ro 최우선

- GMCC Midea R32 R290 rotary inverter compressor
- LG R290 R32 rotary compressor CE certification

### Sc 최우선

- Copeland Emerson YHV ZO ZOD R454B R32 scroll compressor

### 보조 경쟁사

- 정보가 있을 때만 evidence 생성
- Search query는 비용/노이즈를 보며 점진 확대

## 출력

- `outputs/search/YYYY-WW_query_plan.json`
- `outputs/search/YYYY-WW_raw_results.json`
- `outputs/evidence/YYYY-WW_evidence.json`

## 테스트 계획

1. Query Planner 단위 테스트
   - ★ 최우선 경쟁사 query가 반드시 생성되는지
   - Re/Ro/Sc별 최소 query 존재
   - 8개 카테고리 중 우선 카테고리 mapping 검증

2. Evidence Normalizer 테스트
   - raw result → EvidenceItem 변환
   - competitor alias 정규화
   - source trust score 계산
   - 중복 제거

3. Pipeline 테스트
   - stub research result → evidence JSON → STEP 1 writer 전달
   - Critic score 7점 이상 또는 human review flag 검증

## 완료 조건

아래 명령이 통과해야 한다.

```bash
uv run python -m comp_research_mas.cli run-step2-sample
uv run --extra test pytest -q
```

필수 산출물:
- `outputs/search/YYYY-WW_query_plan.json`
- `outputs/search/YYYY-WW_raw_results.json`
- `outputs/evidence/YYYY-WW_evidence.json`
- `outputs/reports/YYYY-MM-DD_compressor_weekly.md`
- `outputs/reviews/YYYY-MM-DD_critic_review.json`

## STEP 2 완료 보고 형식

```text
STEP 2 완료 보고
- 실행 명령:
- 생성 query plan:
- evidence 수:
- source trust score 분포:
- Writer/Critic 결과:
- 테스트 결과:
- 제한/리스크:
- STEP 3 Analyst Agent 진행 여부 확인 필요:
```

## 리스크와 제한

- Hermes 내장 리서치 결과는 네트워크/검색 도구 상태에 따라 달라질 수 있다.
- 공식 소스 접근이 어려우면 industry news로 보완하되 단정 표현을 피한다.
- 가격·유통 카테고리는 아직 미확정이므로 STEP 2에서는 고신뢰 공식 근거가 있을 때만 채택한다.
- 이메일/Obsidian 자동 전달은 STEP 5 전까지 하지 않는다.
