# STEP 2 계획 및 구현 기준 — Search Agent 추가

## 목표

STEP 1 `Writer + Critic self-refine` 루프의 입력을 수동 raw_data에서 자동 선별 evidence bundle로 전환한다.

핵심은 전체 크롤링이 아니라, 타입 × 경쟁사 × 냉매 × 카테고리 조합별로 고신뢰 소스만 제한 검색하고 `EvidenceItem` schema로 정규화하는 것이다.

## STEP 2 확정 구현 범위

- `models.py` schema 확장
- `query_planner.py` 추가
- `research_adapter.py` 추가, stub 우선
- `evidence_normalizer.py` 추가
- `graph.py`를 STEP 2 흐름으로 확장
- `cli.py`에 `run-step2-sample` 추가
- `tests/test_step2.py` 추가
- `AGENTS.md` 추가

## 스키마 기준

### EvidenceItem

필수 필드:

```text
compressor_type : Re / Ro / Sc
competitor      : 정규화된 경쟁사명
refrigerant     : list[str], 복수 냉매 허용
category        : 8개 카테고리 canonical 값
samsung_status  : 보유 / 미보유 / 대응중 / 확인필요
trust_score     : 1~5
source_type     : official / exhibition / patent / academic / trade_media / news
threat_level    : high / medium / low / none
week_id         : YYYY-WW
source_url      : URL
source_date     : YYYY-MM-DD
raw_text        : 원문 요약
```

확장 필드:

```text
product_or_series
condition_or_capacity
application
source_name
is_primary
low_confidence
dynamic_tags
```

### ReportMetadata

```text
week_id
total_evidence_count
type_coverage
competitor_coverage
primary_missing
high_threat_count
critic_score
hard_fail
```

## 동적 태깅 원칙

수집 결과에 따라 `dynamic_tags`를 자동 부여한다.

예시:
- 냉매: `R290`, `R454B`, `R32`
- 기술: `inverter`, `variable`, `two-stage`
- 인증: `certification`
- 성능: `performance`
- 로드맵: `roadmap`

추가 데이터 유형이 발견되면 하드코딩된 리포트 구조를 깨지 않고 `dynamic_tags`에 먼저 반영한다. 태그가 반복적으로 중요해지면 STEP 3에서 정식 schema 필드로 승격한다.

## Query Planner

역할:
- 타입 × 경쟁사 × 카테고리 query plan 생성
- ★ 최우선 경쟁사 우선
- Re/Ro/Sc 각 타입 최소 query 보장
- Secondary 경쟁사는 좁은 범위로 시작해 노이즈를 제한

산출물:

```text
outputs/search/YYYY-WW_query_plan.json
```

## Research Adapter

역할:
- query_plan을 받아 검색 실행
- STEP 2는 stub 우선
- 실제 Hermes 리서치 연결은 repo 밖 Sake/Hermes 레이어가 담당

금지:
- 전체 크롤링
- sitemap 순회
- robots.txt 위반
- 전문 논문/기사 대량 수집

산출물:

```text
outputs/search/YYYY-WW_raw_results.json
```

## Evidence Normalizer

처리 순서:
1. 경쟁사 alias 정규화
2. 카테고리 alias 정규화
3. 냉매 list 추출
4. 삼성 상태 canonical 변환
5. trust_score 산정
6. threat_level 산정
7. trust_score 3 미만은 `low_confidence=True`
8. 동적 태그 생성
9. 중복 제거

중복 제거 기준:

```text
competitor + category + week_id
```

동일 key는 trust_score 높은 항목을 유지한다.

## STEP 2 Graph

```text
source_planner
  → research_adapter
  → evidence_normalizer
  → writer
  → critic
  → conditional:
      score >= 7          → save_output
      score < 7, iter < 2 → writer
      score < 7, iter >= 2→ human_review_flag → save_output
  → END
```

노드별 State 업데이트:

```text
source_planner      → query_plan, week_id
research_adapter    → raw_results
evidence_normalizer → evidence, gap_table, sources
writer              → draft
critic              → score, feedback, hard_fail
save_output         → report_meta, 파일 저장
```

## 테스트 계획

- EvidenceItem 태깅 필드 전체 존재 확인
- ReportMetadata 생성 확인
- query_planner: Re/Ro/Sc 타입별 최소 query 수
- query_planner: ★ 최우선 경쟁사 query 우선 포함
- evidence_normalizer: alias 정규화
- evidence_normalizer: trust_score 계산
- evidence_normalizer: threat_level 산정
- evidence_normalizer: 중복 제거
- 전체 그래프 E2E, stub 기반
- 기존 STEP 1 테스트 호환성 유지

## 완료 조건

```bash
uv run python -m comp_research_mas.cli run-step2-sample
uv run --extra test pytest -q
```

산출물 5개:

```text
outputs/search/YYYY-WW_query_plan.json
outputs/search/YYYY-WW_raw_results.json
outputs/evidence/YYYY-WW_evidence.json
outputs/reports/YYYY-MM-DD_compressor_weekly.md
outputs/reviews/YYYY-MM-DD_critic_review.json
```

## STEP 3 전 확인 필요

- 실제 Hermes 리서치 연결 방식
- 가격·유통 카테고리 사용 범위
- 특허·인증 지역 우선순위
- 내부 삼성 매핑 레이어 도입 범위
