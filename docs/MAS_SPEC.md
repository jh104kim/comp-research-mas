# MAS 기획서 — C&M 압축기 경쟁사 모니터링

## 시스템 개요

| 항목 | 내용 |
|---|---|
| 목적 | 경쟁사 신제품·스펙·특허·동향 자동 수집 및 주간 리포트 생성 |
| 대상 냉매·타입 | R290 Reciprocating / R454B Scroll / Rotary, 가정용·Unitary·Heat pump |
| 실행 주기 | 매주 월요일 자동 트리거 |
| 출력 | 이메일 발송 + Obsidian 노트 저장 |

## 에이전트 역할 정의

### Orchestrator

- 주간 실행 트리거 수신
- Search → Analyst → Writer → Critic 순서 지휘
- 실패 시 재시도·대체 경로 결정
- Critic 기준 미달 시 Writer 재작성 지시

### Search Agent

수집 소스:
- 공식 웹사이트
- Google Patents
- 전시회 보도자료
- 업계 뉴스

경쟁사별 수집 범위:

| 그룹 | 대상사 | 주요 모니터링 항목 |
|---|---|---|
| R290 Re 핵심 | Embraco/Nidec, Secop, GMCC | EM/NEK/NT, KL/NL/DL, PA/KA 신모델 |
| R454B Sc 핵심 | GMCC, Danfoss, LG, Copeland | DSH, YPH/YBH, YHV/ZO 스펙 변경 |
| 보조 모니터링 | LG, Panasonic | CMA, E-Series 인버터 동향 |
| 별도 관리 | Highly | Rotary 중심 별도 트래킹 |

### Analyst Agent

- R290 Re 벤치마크: Samsung Gap Matrix 기준 비교
- R454B Sc 벤치마크: 조건 정규화 후 성능 비교
- 신규 특허·기술 논문 요약
- 이상 신호 탐지: 급격한 스펙 변경, 신규 냉매 전환 등

### Writer Agent

주간 리포트 초안 생성:
1. 이번 주 핵심 동향, 3줄 요약
2. 경쟁사별 신규 정보
3. R290 Re Gap 현황 업데이트
4. R454B Sc 벤치마크 변동
5. 주목할 특허·기술
6. 다음 주 모니터링 포인트

### Critic Agent, Self-Refine

평가 기준:
- 사실 확인: 출처 명시 여부
- 누락 경쟁사 없는지 체크
- Samsung Gap 관점 반영 여부
- 가독성·분량 적절성: A4 1~2장

기준 미달 시 Writer에 피드백하고 최대 2회 재작성한다.

## 기술 스택

| 레이어 | 선택 |
|---|---|
| Orchestration | LangGraph, 노드·엣지·조건부 흐름 |
| LLM | Claude Sonnet, 추론·작성 |
| Search Tool | Web Search + Google Patents API |
| Memory | 벡터DB, 과거 리포트 + Obsidian, Episodic |
| Output | 이메일 API, SMTP + Obsidian Markdown |

## 구현 단계

```text
1단계: Writer + Critic 루프만
   → 수동으로 검색 결과 붙여넣기 → 리포트 생성·정제
2단계: Search Agent 추가
   → 자동 웹 수집 연결
3단계: Analyst Agent 추가
   → Samsung Gap Matrix 기준 자동 비교
4단계: Orchestrator + 스케줄러
   → 주 1회 완전 자동 실행
5단계: 출력 자동화
   → 이메일 발송 + Obsidian 저장 연결
```
