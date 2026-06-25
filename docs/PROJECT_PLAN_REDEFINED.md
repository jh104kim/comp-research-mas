# C&M 압축기 경쟁사 모니터링 MAS — 프로젝트 계획 재정의안

## 전제 변화

기존 Phase 1 MVP는 수동 입력 기반 Writer + Critic 리포트 생성기였으나, 새 메타 프롬프트 기준에서는 다음 요구사항을 우선 반영한다.

- 구현 기준: **Python + LangGraph** 중심 MAS.
- LLM 연결: **Codex 연결 API 사용**, 별도 API Key를 새로 요구하지 않는다.
- 리서치 방식: Hermes 내장 리서치/검색 역량을 활용하되 **전체 크롤링은 금지**한다.
- 소스 정책: 웹 전체를 긁지 않고, **멘션·인용·신뢰도가 높은 주요 소스만 선별**한다.
- 모니터링 범위: Re/Ro/Sc 전 타입을 포함하고, 냉매를 R290/R454B 등 특정 타입에 고정하지 않는다.
- 분석 관점: 특정 냉매 추적이 아니라 **삼성 경쟁 라인업 관점의 포괄 추적**을 기본으로 한다.

---

## 1) MAS 굵은 뼈대

### 1.1 핵심 목적

C&M 압축기 경쟁사 동향을 주간 단위로 선별 수집·분류·분석·비교·작성·검증하여, 삼성 관점에서 의미 있는 경쟁 신호를 보고서화한다.

### 1.2 최종 리포트 구조

```text
Level 1: 압축기 타입
- Re: Reciprocating
- Ro: Rotary
- Sc: Scroll

Level 2: 8개 모니터링 카테고리
1. 신냉매·냉매 전환
2. 성능·효율
3. 신제품·라인업
4. 신뢰성·내구성
5. 특허·기술
6. 규격·인증
7. 가격·유통
8. 전시회·발표

Level 3: 경쟁사별 내용 + 삼성 비교 관점
- 경쟁사/제품/라인업별 핵심 변화
- 출처 URL, 출처 유형, 날짜, 신뢰도
- 삼성 라인업 대비 위협·기회·확인 필요 사항
```

### 1.3 주요 에이전트

| 에이전트 | 역할 |
|---|---|
| Orchestrator | LangGraph StateGraph로 전체 흐름 제어, 조건부 재작성, 실패 처리 |
| Source Selector | 공식 발표·특허·인증·전시회·고인용 뉴스 등 선별 소스 후보 구성 |
| Research Agent | Hermes 내장 리서치로 제한된 범위의 고신뢰 자료 수집 |
| Evidence Normalizer | 원자료를 표준 schema로 정규화: 타입, 카테고리, 경쟁사, 날짜, URL, 근거 강도 |
| Analyst Agent | Re/Ro/Sc 및 8개 카테고리별 경쟁 신호와 삼성 비교 관점 도출 |
| Writer Agent | 정해진 3계층 구조의 주간 리포트 초안 작성 |
| Critic Agent | 근거성, 구조 준수, 커버리지, 삼성 비교 관점, 과장 여부를 0~10점 평가 |
| Output Agent | Markdown/JSON 저장, 향후 Obsidian·이메일 연동 |

---

## 2) 에이전틱 AI Workflow

### 2.1 Step 1 — Writer + Critic self-refine loop

새 요구사항에 맞춰 Step 1도 단순 Writer/Critic이 아니라 LangGraph 상태 모델을 먼저 고정한다.

#### State

```python
state = {
    "raw_data": list,      # 수동 또는 Hermes 리서치로 확보한 선별 근거
    "draft": str,         # Writer가 생성한 리포트 초안
    "feedback": dict,     # Critic 피드백
    "score": float,       # 0~10점
    "iteration": int      # 재작성 횟수
}
```

#### 조건부 흐름

```text
START
  → load_raw_data
  → writer
  → critic
  → if score >= 7: save_output
  → if score < 7 and iteration < 2: writer_rewrite
  → if score < 7 and iteration >= 2: save_with_human_review_flag
  → END
```

#### Critic 평가 기준, 0~10점

- 구조 준수: Re/Ro/Sc → 8개 카테고리 → 경쟁사별 삼성 비교 관점.
- 근거 품질: URL, 날짜, 출처 유형, 고신뢰/고인용 여부.
- 범위 적합성: 특정 냉매나 특정 타입에 편중되지 않았는지.
- 분석 품질: 삼성 라인업 관점의 위협·기회·추가 확인 사항 도출.
- 안전성: 과장, 추측, 내부 민감정보 노출 방지.

7점 미만이면 Writer가 Critic 피드백을 반영해 최대 2회 재작성한다.

### 2.2 Step 2 이후 전체 Workflow

```text
1. Source Planning
   - 이번 주 확인할 경쟁사, 제품군, 전시회, 특허, 인증, 뉴스 소스 후보 생성

2. Selective Research
   - 전체 크롤링 금지
   - 공식/특허/인증/전시회/고신뢰 업계 매체 중심으로 제한 검색

3. Evidence Normalization
   - 모든 발견 사항을 표준 EvidenceItem으로 변환
   - Re/Ro/Sc, 8개 카테고리, 경쟁사, 제품, 냉매, 출처, 날짜 태깅

4. Analysis
   - 삼성 경쟁 라인업 관점으로 의미 있는 변화만 추출
   - 단순 뉴스 요약이 아니라 영향도/확실도/후속 확인 필요성 평가

5. Report Writing
   - Level 1/2/3 구조로 리포트 작성
   - 중요한 공백도 명시: “이번 주 확인된 고신뢰 근거 없음”

6. Critic Review
   - 0~10점 평가
   - 7점 미만이면 최대 2회 self-refine

7. Output
   - Markdown 리포트
   - JSON evidence bundle
   - Critic review JSON
```

---

## 3) 단계별 구현 계획

### Phase 0 — 요구사항·스키마 재정의

목표:
- 기존 R290 Re/R454B Sc 중심 기획을 Re/Ro/Sc 전체 범위로 확장한다.
- 8개 카테고리와 삼성 비교 관점을 데이터 모델에 반영한다.

구현:
- `EvidenceItem`, `ReportSection`, `CriticReview`, `WorkflowState` 모델 정의.
- 경쟁사/제품/소스 registry 초안 작성.
- 냉매 필드는 필수 고정값이 아니라 optional/multi-value로 둔다.

완료 기준:
- 샘플 evidence가 Re/Ro/Sc, 8개 카테고리로 분류된다.
- 기존 특정 냉매 중심 문구가 제거된다.

### Phase 1 — LangGraph Writer + Critic MVP

목표:
- 실제 자동 리서치 전, 수동/샘플 raw_data를 받아 LangGraph self-refine loop를 구현한다.

구현:
- LangGraph StateGraph 구성.
- 노드: `load_raw_data`, `writer`, `critic`, `save_output`.
- State: `raw_data`, `draft`, `feedback`, `score`, `iteration`.
- Critic 0~10점, 7점 미만 최대 2회 재작성.
- Codex 연결 API를 LLM 호출 abstraction 뒤에 둔다.

완료 기준:
- 샘플 입력으로 리포트 Markdown, evidence JSON, critic JSON 생성.
- 테스트에서 재작성 조건부 edge가 검증된다.

### Phase 2 — Hermes 내장 Research 연동, 제한 검색

목표:
- 전체 크롤링 없이 고신뢰 소스만 선별 조사한다.

구현:
- Source Selector가 소스 우선순위를 정한다.
  - 1순위: 경쟁사 공식 발표/제품 페이지/카탈로그
  - 2순위: 특허/인증/규격 DB
  - 3순위: 전시회 발표 자료
  - 4순위: 업계 전문 매체 중 반복 인용·멘션이 높은 기사
- Hermes 리서치 결과를 EvidenceItem으로 정규화한다.
- 동일 사건 중복 제거와 출처 신뢰도 점수화.

완료 기준:
- 임의 주차에 대해 10~30개 내외의 선별 evidence bundle 생성.
- 무차별 사이트 크롤링 없이 소스 로그가 남는다.

### Phase 3 — Analyst Agent 고도화

목표:
- 단순 요약이 아니라 삼성 경쟁 라인업 관점의 비교 분석을 생성한다.

구현:
- Re/Ro/Sc별 주요 경쟁사/제품군 registry 작성.
- 8개 카테고리별 분석 prompt와 scoring rubric 정의.
- 영향도, 확실도, 대응 필요도 필드 추가.
- 냉매 전환은 특정 냉매 고정이 아니라 경쟁사 라인업 변화의 한 축으로 처리.

완료 기준:
- 경쟁사별 내용마다 삼성 관점의 의미가 1개 이상 도출된다.
- 근거 없는 추론은 `확인 필요`로 분리된다.

### Phase 4 — 주간 실행·저장 자동화

목표:
- 주 1회 실행 가능한 운영 흐름을 만든다.

구현:
- CLI: `run-weekly`, `run-sample`, `validate-evidence`.
- 출력 경로 표준화:
  - `outputs/reports/YYYY-WW-weekly-report.md`
  - `outputs/evidence/YYYY-WW-evidence.json`
  - `outputs/reviews/YYYY-WW-critic.json`
- 실패 시 human review flag 생성.

완료 기준:
- 한 명령으로 주간 리포트와 검증 파일이 생성된다.

### Phase 5 — 배포/운영 확장

목표:
- Obsidian 저장, 이메일, 스케줄러 등 운영 자동화를 붙인다.

구현:
- Obsidian Markdown 저장 경로 연동.
- 이메일 발송은 승인 후 적용.
- 실행 로그와 비용/호출량 추적.
- 이전 주 리포트와 변화점 비교 기능 추가.

완료 기준:
- 주간 실행 결과가 지정 저장소에 축적된다.
- 실패·저신뢰 결과는 자동 발송하지 않고 검토 대기로 남긴다.

---

## 4) 제한해야 할 것

1. **전체 크롤링 금지**
   - 사이트맵 전체 수집, 무차별 페이지 순회, 대량 scraping 금지.

2. **냉매 범위 고정 금지**
   - R290, R454B 등 특정 냉매만 추적 대상으로 고정하지 않는다.
   - 냉매는 경쟁 라인업 변화의 속성으로 취급한다.

3. **타입 편중 금지**
   - Re/Ro/Sc 중 특정 타입만 반복 분석하지 않는다.
   - 정보가 없으면 “확인된 고신뢰 근거 없음”으로 명시한다.

4. **출처 없는 주장 금지**
   - 제품 성능, 효율, 가격, 인증, 특허 내용은 반드시 URL/날짜/출처 유형을 붙인다.

5. **저신뢰 자료의 단정 금지**
   - 커뮤니티, 단일 블로그, 미확인 리셀러 정보는 보조 단서로만 사용한다.

6. **삼성 내부정보 노출 금지**
   - 내부 스펙, 미공개 로드맵, 원가, 고객 정보 등은 입력·출력에 포함하지 않는다.

7. **과도한 자동 발송 금지**
   - Critic 7점 미만, 출처 부족, 민감정보 의심 시 이메일 자동 발송하지 않는다.

8. **별도 API Key 전제 금지**
   - LLM은 Codex 연결 API abstraction을 기본으로 하며, 사용자에게 새 키 입력을 요구하지 않는다.

---

## 5) 애매해서 사용자에게 물어볼 질문

1. 경쟁사 범위는 어디까지인가?
   - 예: GMCC, Highly, Panasonic, LG, Danfoss, Copeland, Secop, Embraco/Nidec 외 추가 대상 여부.

2. “삼성 경쟁 라인업”의 기준 제품군은 무엇인가?
   - Re/Ro/Sc별 비교 기준 모델, 용량대, 적용처를 어디까지 둘지 확인 필요.

3. 주간 리포트의 깊이는 어느 정도가 적절한가?
   - 임원용 1~2페이지 요약인지, 실무자용 상세 evidence appendix 포함인지.

4. 소스 우선순위에서 반드시 포함해야 하는 사이트가 있는가?
   - 공식 홈페이지, 특허 DB, 인증 DB, 전시회, 업계 매체의 whitelist 필요.

5. 가격·유통 정보의 허용 범위는 어디까지인가?
   - 공개 리셀러 가격, 견적성 자료, 지역별 유통 정보 사용 가능 여부.

6. 냉매 전환 카테고리에서 추적해야 할 핵심 냉매군이 있는가?
   - 고정은 피하되, 우선순위 냉매군을 둘 수 있는지 확인 필요.

7. 리포트 발송/저장 위치는 어디인가?
   - Obsidian 경로, 이메일 수신자, 자동 발송 승인 조건 확인 필요.

8. Hermes 내장 리서치 결과와 외부 검색 결과의 감사 로그 수준은 어느 정도 필요한가?
   - 검색어, 검색 시각, 제외 소스, 채택 이유까지 남길지 결정 필요.

9. Critic 합격선 7점 외에 hard fail 조건이 필요한가?
   - 출처 0개, 특정 타입 누락, 삼성 비교 관점 누락 등을 즉시 실패 처리할지 확인 필요.

10. 특허·인증 정보의 지역 범위는 어디까지인가?
    - US/EU/CN/KR/JP 중 우선순위와 필수 DB 지정 필요.

---

## 우선 다음 액션

1. 기존 `docs/MAS_SPEC.md`, `docs/PROJECT_PLAN.md`를 본 재정의안 기준으로 정리한다.
2. Phase 1 코드를 LangGraph StateGraph 기반으로 재작성한다.
3. `EvidenceItem`과 `WorkflowState` schema를 먼저 고정한다.
4. 샘플 데이터를 Re/Ro/Sc × 8개 카테고리 구조에 맞게 교체한다.
5. Critic 0~10점, 7점 미만 최대 2회 재작성 테스트를 추가한다.
