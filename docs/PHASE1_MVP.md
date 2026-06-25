# STEP 1 — Writer + Critic Self-Refine Loop

## 목표

수동 입력 `raw_data`를 받아 압축기 경쟁사 주간 리포트를 생성하고, Critic이 구조·삼성 비교 관점·Gap 표·출처·경쟁사 누락·가독성을 평가한다. 7점 미만이면 Writer가 최대 2회 재작성한다.

## LangGraph 최소 흐름

```text
START
  → load_raw_data
  → writer
  → critic
  → conditional_refine
      score >= 7 → save_output
      score < 7 and iteration < 2 → writer
      score < 7 and iteration >= 2 → save_with_human_review_flag
  → END
```

## State 구조

```python
class WorkflowState(TypedDict):
    raw_data: str | list[EvidenceItem]
    draft: str
    feedback: str | dict
    score: int
    iteration: int
    status: str
```

## Writer 요구사항

Writer는 아래 리포트 구조를 완전 준수한다.

```text
Level 1: Re / Ro / Sc
  Level 2: 8개 카테고리
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

규칙:
- 정보 없는 카테고리도 공란 금지
- `해당 없음 — 이번 주 확인된 고신뢰 근거 없음`으로 명시
- 각 항목에는 `내용 / 삼성 비교 관점 / 출처` 포함
- 삼성 Gap 종합 현황 표 생성
- 출처 목록 생성

## Critic 평가 기준

총 10점:

| 평가 항목 | 점수 |
|---|---:|
| Re/Ro/Sc + 8개 카테고리 + 경쟁사별 구조 준수 | 2 |
| 삼성 비교 관점 모든 주요 항목 반영 | 3 |
| 삼성 Gap 표 정확성/구조 | 2 |
| 출처 명시 여부 | 1 |
| 경쟁사 누락 없는지 | 1 |
| 분량·가독성 | 1 |

판정:
- 7점 이상: 통과
- 7점 미만: Writer 재작성
- 최대 2회 반복 후 human review flag

Hard fail:
- 출처 목록 0개
- Re/Ro/Sc 중 전체 타입 누락
- 삼성 비교 관점 전체 누락
- 민감정보 의심 문자열 발견
- fabrication risk high

## 테스트용 raw_data

```text
[Re - Embraco/Nidec]
NEK2150U R290 신모델 출시.
COP 1.32, 냉동능력 165W, MBP 조건.
기존 대비 효율 8% 향상.
삼성 동급 R290 MBP 모델 미보유.
출처: Embraco product news, 2026-06-25

[Re - Secop]
SC10CL R290 MBP 고효율 스펙 업데이트.
UL 인증 신규 취득.
삼성 R290 MBP 구간 미대응 상태.
출처: Secop product page, 2026-06-25

[Re - GMCC]
KA90 R600a 신모델 유럽 출하 시작.
삼성 R600a Re 라인업 부재.
출처: GMCC release, 2026-06-25

[Sc - GMCC]
PA135M2CS R454B Fixed Scroll 신규 출시.
EER 3.45, 3RT 구간.
삼성 동급 구간 대응 중.
출처: GMCC catalog, 2026-06-25

[Sc - Danfoss]
DSH R454B Variable Scroll 로드맵 공개.
2026년 양산 예정.
삼성 Variable Scroll 미보유.
출처: Danfoss roadmap news, 2026-06-25

[Ro - Highly]
R290 Rotary 신모델 CE 인증 완료.
삼성 R290 Rotary 라인업 현황 확인 필요.
출처: Highly certification news, 2026-06-25
```

## 구현 파일

- `src/comp_research_mas/models.py`
- `src/comp_research_mas/agents.py`
- `src/comp_research_mas/graph.py`
- `src/comp_research_mas/tools.py`
- `src/comp_research_mas/output.py`
- `src/comp_research_mas/config.py`
- `src/comp_research_mas/cli.py`
- `examples/manual_search_results/step1_raw_data.md`
- `tests/test_step1_langgraph.py`

## 완료 조건

명령:

```bash
uv run python -m comp_research_mas.cli run-step1-sample
uv run --extra test pytest -q
```

필수 산출물:
- `outputs/reports/YYYY-MM-DD_compressor_weekly.md`
- `outputs/reviews/YYYY-MM-DD_critic_review.json`
- `outputs/evidence/YYYY-MM-DD_evidence.json` 또는 raw snapshot

필수 확인:
- Re/Ro/Sc 구조 존재
- 각 타입마다 8개 카테고리 존재
- 경쟁사별 세부 내용 존재
- 삼성 비교 관점 존재
- 삼성 Gap 표 존재
- 출처 목록 존재
- Critic 점수와 iteration 기록 존재

## STEP 1 완료 보고 형식

```text
STEP 1 완료 보고
- 실행 명령:
- 생성 리포트:
- Critic 점수:
- 재작성 횟수:
- 테스트 결과:
- 누락/리스크:
- STEP 2 진행 여부 확인 필요:
```
